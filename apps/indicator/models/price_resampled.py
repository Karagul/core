import pandas as pd
import numpy as np
#import talib.stream as tas
import logging

from django.db import models
from unixtimestampfield.fields import UnixTimeStampField
from datetime import timedelta, datetime
from apps.channel.models.exchange_data import SOURCE_CHOICES
from apps.indicator.models.abstract_indicator import AbstractIndicator
from apps.signal.models import Signal
from apps.user.models.user import get_horizon_value_from_string

from settings import HORIZONS   # mapping from bin size to a name short/medium
from settings import time_speed # speed of the resampling, 10 for fast debug, 1 for prod

logger = logging.getLogger(__name__)

class PriceResampled(AbstractIndicator):
    # source inherited from AbstractIndicator
    # coin inherited from AbstractIndicator
    # timestamp inherited from AbstractIndicator

    period = models.PositiveSmallIntegerField(null=False, default=15)  # minutes (eg. 15)

    mean_price_satoshis = models.IntegerField(null=True) # price_satoshis
    min_price_satoshis = models.IntegerField(null=True) # price_satoshis
    max_price_satoshis = models.IntegerField(null=True) # price_satoshis

    SMA50_satoshis = models.IntegerField(null=True) # price_satoshis
    SMA200_satoshis = models.IntegerField(null=True) # price_satoshis

    EMA50_satoshis = models.IntegerField(null=True) # price_satoshis
    EMA200_satoshis = models.IntegerField(null=True) # price_satoshis

    relative_strength = models.FloatField(null=True) # relative strength
    # RSI = relative strength index, see property

    _resampled_price_ts = None

    # MODEL PROPERTIES

    @property
    def relative_strength_index(self): # relative strength index
        if self.relative_strength is not None:
            return 100.0 - (100.0 / (1.0 + self.relative_strength))


    # MODEL FUNCTIONS
    def get_price_ts(self):
        '''
        Caches from DB the min nessesary amount of records to calculate SMA, EMA etc
        :return: pd.Series of last 200 time points
        '''
        if self._resampled_price_ts is None:
            back_in_time_records = list(PriceResampled.objects.filter(
                period=self.period,
                coin=self.coin,
                timestamp__gte = datetime.now() - timedelta(minutes=(self.period*200+50)) # 50 is for safety
            ).values('mean_price_satoshis'))

            if not back_in_time_records:
                return None

            self._resampled_price_ts = pd.Series([rec['mean_price_satoshis'] for rec in back_in_time_records])
            # TALIB: price_ts_nd = np.array([ rec['mean_price_satoshis'] for rec in raw_data])

        return self._resampled_price_ts


    def calc_SMA(self):
        price_ts = self.get_price_ts()

        if price_ts is not None:  # if we have at least one timepoint (to avoid ta-lib SMA error, not nessesary for pandas)
            # calculate SMA and save it in the same record
            # TALIB: price_ts_nd = np.array([ rec['mean_price_satoshis'] for rec in raw_data])
            SMA50 = price_ts.rolling(window=int(50/time_speed), center=False, min_periods=4).mean()
            SMA50 = float(SMA50.tail(1))
            SMA200 = price_ts.rolling(window=int(200/time_speed), center=False, min_periods=4).mean()
            SMA200 = float(SMA200.tail(1))

            # TALIB:_SMA50 = tas.SMA(price_ts_nd.astype(float), timeperiod=50/time_speed)
            # TALIB:_MA200 = tas.SMA(price_ts_nd.astype(float), timeperiod=200/time_speed)

            if not np.isnan(SMA50):
                self.SMA50_satoshis = SMA50
            if not np.isnan(SMA200):
                self.SMA200_satoshis = SMA200


    def calc_EMA(self):
        price_ts = self.get_price_ts()

        # alpha is a decay constant which tells how much back in time
        # the decay make the contribution of the time point negledgibly small
        alpha50 = 2.0 / (50+1)
        alpha200 = 2.0 / (200 + 1)

        if price_ts is not None:
            EMA50 = price_ts.ewm(alpha=alpha50, min_periods=5).mean()
            EMA50 = float(EMA50.tail(1))  # get the last value for "now" time point
            EMA200 = price_ts.ewm(alpha=alpha200, min_periods=5).mean()
            EMA200 = float(EMA200.tail(1))

            if not np.isnan(EMA50):
                self.EMA50_satoshis = EMA50
            if not np.isnan(EMA200):
                self.EMA200_satoshis = EMA200


    def calc_RS(self):
        '''
        Relative Strength calculation.
        The RSI is calculated a a property, we only save RS
        (RSI is a momentum oscillator that measures the speed and change of price movements.)
        :return:
        '''
        price_ts = self.get_price_ts()

        delta = price_ts.diff()
        up, down = delta.copy(), delta.copy()

        up[up < 0] = 0
        down[down > 0] = 0

        rUp = up.ewm(com=self.period - 1, adjust=False).mean()
        rDown = down.ewm(com=self.period - 1, adjust=False).mean().abs()
        rs_ts = rUp / rDown   # time series for all values
        self.relative_strength = float(rs_ts.tail(1))  # get the last element for the last time point

        #rsi = 100 - 100 / (1 + rUp / rDown)




    def check_signal(self):
        """
        Check and emit all possible signals to SQS
        :return:
        """

        # List of all indicators to calculate signals
        INDICATORS = [
            {'low':'SMA50_satoshis', 'high':'SMA200_satoshis', 'name':'SMA'},
            {'low':'EMA50_satoshis', 'high':'EMA200_satoshis', 'name':'EMA'}
        ]

        # get DB records for the last two time points
        last_two_rows = list(
            PriceResampled.objects.
                filter(period=self.period, coin=self.coin).
                order_by('-timestamp').
                values('mean_price_satoshis', 'SMA50_satoshis','SMA200_satoshis','EMA50_satoshis','EMA200_satoshis'))[0:2]

        # Sanity check:
        if not last_two_rows:
            logger.debug('Signal skipped: There is no information in DB about ' + str(self.coin) + str(self.period))
            exit()

        prices = np.array([row['mean_price_satoshis'] for row in last_two_rows])
        if any(prices) is None: exit()

        # check and emit SMA, EMA signals
        # iterate through all metrics which might generate signals, SMA, EMA etc

        for ind in INDICATORS:
            # get last two time points from indicators ( SMA20, SMA200 etc)
            m_low  = np.array([row[ind['low']] for row in last_two_rows])
            m_high = np.array([row[ind['high']] for row in last_two_rows])

            horizon = get_horizon_value_from_string(display_string=HORIZONS[self.period])

            # check if ind_A signal changes its sign
            if all(m_low != None):  # now we know both price and low exists
                ind_A_sign = np.sign(prices - m_low)   # [-1, 1]

                if np.prod(ind_A_sign) < 0:  # emit a signal if indicator changes its sign
                    #logger.debug("Ind_A sign difference:" + str(ind_A_sign))
                    signal_A = Signal(
                        coin=self.coin,
                        signal=ind['name'],
                        trend=int(ind_A_sign[0]),
                        horizon=horizon,
                        strength_value=int(1),  # means A indicator
                        strength_max=int(3),
                        timestamp=self.timestamp
                    )
                    signal_A.save() # saving will send immediately if not already sent
                    signal_A.print()

            if all(m_high != None):
                ind_B_sign = np.sign(prices - m_high)

                if np.prod(ind_B_sign) < 0:   # if change the sign
                    #logger.debug("Ind_B sign difference:" + str(ind_B_sign))
                    signal_B = Signal(
                        coin=self.coin,
                        signal=ind['name'],
                        trend=int(ind_B_sign[0]),
                        horizon=horizon,
                        strength_value=int(2),  # means B indicator
                        strength_max=int(3),
                        timestamp=self.timestamp
                    )
                    signal_B.save() # saving will send immediately if not already sent
                    signal_B.print()

            if all(m_high != None) and all(m_low != None):
                ind_C_sign = np.sign(m_low - m_high)

                if np.prod(ind_C_sign) < 0 :
                    #logger.debug("Ind_C sign difference:" + str(ind_C_sign))
                    signal_C = Signal(
                        coin=self.coin,
                        signal=ind['name'],
                        trend=int(ind_C_sign[0]),
                        horizon=horizon,
                        strength_value=int(3),   # means C indicator
                        strength_max=int(3),
                        timestamp=self.timestamp
                    )
                    signal_C.save() # saving will send immediately if not already sent
                    signal_C.print()


        # emit RSI every time I calculate it
        '''
        alert_RSI = TelegramAlert(
            coin=self.coin,
            signal="RSI",

        )
        alert_RSI.print()
        alert_RSI.send()
        '''
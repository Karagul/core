from settings import LOAD_TALIB

if LOAD_TALIB:
    import talib

from apps.TA import HORIZONS
from apps.TA.storages.abstract.indicator import IndicatorStorage
from apps.TA.storages.abstract.indicator_subscriber import IndicatorSubscriber
from apps.TA.storages.data.price import PriceStorage
from settings import logger


class MomStorage(IndicatorStorage):

    def produce_signal(self):
        pass


class MomSubscriber(IndicatorSubscriber):
    classes_subscribing_to = [
        PriceStorage
    ]

    def handle(self, channel, data, *args, **kwargs):

        self.index = self.key_suffix

        if self.index is not 'close_price':
            logger.debug(f'index {self.index} is not `close_price` ...ignoring...')
            return

        new_mom_storage = MomStorage(ticker=self.ticker,
                                     exchange=self.exchange,
                                     timestamp=self.timestamp)

        for horizon in HORIZONS:
            periods = horizon * 10

            close_value_np_array = self.get_values_array_from_query(
                PriceStorage.query(
                    ticker=self.ticker,
                    exchange=self.exchange,
                    index='close_price',
                    periods_range=periods
                ),
                limit=periods)

            timeperiod = min([len(close_value_np_array), periods])
            mom_value = talib.MOM(close_value_np_array, timeperiod=timeperiod)[-1]
            logger.debug(f'saving Mom value {mom_value} for {self.ticker} on {periods} periods')

            new_mom_storage.periods = periods
            new_mom_storage.value = int(float(mom_value))
            new_mom_storage.save()
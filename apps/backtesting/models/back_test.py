import logging
import time
from unixtimestampfield.fields import UnixTimeStampField
from django.db import models
from apps.strategy.models.rsi_sma_strategies import *
from apps.strategy.models.ai_strategies import *
from apps.strategy.models.ichi_strategies import *
from apps.indicator.models.price_resampl import get_price_at_timepoint, PriceResampl
from apps.signal.models.signal import ALL_SIGNALS
from datetime import datetime
from apps.indicator.models.price import Price
from settings import PERIODS_LIST
import pandas as pd
from enum import Enum

logger = logging.getLogger(__name__)

CURRENCY_NAMES = {
    0: "BTC",
    1: "ETH",
    2: "USDT",
    3: "XMR"
}

class BacktestStatus(Enum):
    OK = 'OK'
    PRICE_ERROR = 'PR_ERR'

START_CASH = 1000


class BackTest(models.Model):
    '''
    This is a log of all backtesting runs.
    For each backtest run we have one record in db with resulted metrics
    '''

    # starting time of backtesting
    timestamp = UnixTimeStampField(null=False)

    # strategy name
    strategy_class_name = models.CharField(max_length=64, null=False)

    # start of time period being backtested
    start_timeframe = UnixTimeStampField(null=False)

    # end of time period being backtested
    end_timeframe = UnixTimeStampField(null=False)

    # transaction currency
    transaction_currency = models.CharField(max_length=6, null=False, blank=False)

    # counter currency
    counter_currency = models.SmallIntegerField(null=False)

    # resample period
    resample_period = models.PositiveSmallIntegerField(null=False)

    # profit percent to counter currency
    profit_percent = models.FloatField(null=True)

    # profit percent to counter currency with conversion of initial and end values to USDT
    profit_percent_USDT = models.FloatField(null=True)

    # number of trades
    num_trades = models.FloatField(null=True)

    # number of profitable trade pairs
    num_profitable_trade_pairs = models.FloatField(null=True)

    # avg profit percent per trade pair (buy, sell)
    avg_profit_per_trade_pair = models.FloatField(null=True)

    # number of buys
    num_buys = models.FloatField(null=True)

    # number of sells
    num_sells = models.FloatField(null=True)

    # buy and hold profit percent (buy on start_timeframe, get value on end_timeframe)
    buy_and_hold_profit_percent = models.FloatField(null=True)

    # buy and hold profit percent with conversion of start and end value to USDT
    buy_and_hold_profit_percent_USDT = models.FloatField(null=True)

    # percent gain of strategy compared to buying and holding
    percent_gain_over_buy_and_hold = models.FloatField(null=True)

    # percent gain of strategy compared to buying and holding in USDT
    percent_gain_over_buy_and_hold_USDT = models.FloatField(null=True)

    # calculation status
    status = models.CharField(max_length=6, null=False, blank=False)

    def __init__(self, strategy_class_name, start_timeframe, end_timeframe):
        # see https://stackoverflow.com/questions/24537091/error-no-attribute-state
        super(BackTest, self).__init__()

        self.strategy_class_name = str(strategy_class_name).split(".")[-1][:-2]  # TODO: fix the received names
        self.start_timestamp = start_timeframe   # we need to keep this separately, as Django fields are autocast to datetime
        self.end_timestamp = end_timeframe
        self.timestamp = end_timeframe

    def run_backtest_on_one_curency_pair(self, source, transaction_currency, counter_currency, resample_period):
        """
        Backtests the strategy given in the class constructor for one currency pair on one exchanger.
        :param source: exchanger ID
        :param transaction_currency: currency being traded
        :param counter_currency: counter currency
        :param resample_period: horizon information
        :return:
        """

        # TODO: perhaps move strategy and signal init to constructor?
        # create strategy object from name
        strategy = init_strategy(strategy_name=self.strategy_class_name, transaction_currency=transaction_currency,
                                 counter_currency=counter_currency, source=source, timestamp=self.timestamp,
                                 resample_period=resample_period)

        # extract all strategy signals
        signals = strategy.get_all_signals_in_time_period(self.start_timestamp, self.end_timestamp)

        # simulate trading based on strategy signals
        dict = self.simulate_trading(signals, START_CASH, transaction_currency, counter_currency,
                                   self.start_timestamp, self.end_timestamp, resample_period, source)
        if dict is not None:
            self.create_row_and_save(transaction_currency, counter_currency, resample_period, dict)
        return dict


    def run_backtest_on_several_currency_pairs(self):
        # allow moving all money into another currency
        # TODO: need signals from Alex to carry currency info
        pass

    def run_backtest_on_all_currency(self):
        """
        Backtests the strategy provided in the constructor on all currency pairs and all exchangers and
        computes aggregated statistics.
        """

        # TODO: decide which tuples we will use in the end
        tuples = get_all_currency_tuples()

        # iterate over all currencies and exchangers (POLONIEX etc) with run_backtest_on_one_curency_pair
        logger.info("Started backtesting on all currency...")
        strategy_backtest_results = None

        #atomic_tuples = [(0, 'BTC', 2), (0, 'ETH', 0)] # generate all triples you need (source/transact_curr/counter_curr)
        #for source, transaction_currency, counter_currency in atomic_tuples:
        for tuple in tuples:
            for resample_period in PERIODS_LIST:
                source = tuple["source"]
                transaction_currency = tuple["transaction_currency"]
                counter_currency = tuple["counter_currency"]
                backtest_result = self.run_backtest_on_one_curency_pair(source, transaction_currency, counter_currency, resample_period)
                if backtest_result is None:  # the strategy generated no trades
                    continue
                backtest_result_df = pd.DataFrame.from_records([backtest_result])
                self.create_row_and_save(transaction_currency, counter_currency, resample_period, backtest_result)
                if strategy_backtest_results is None:
                    strategy_backtest_results = backtest_result_df
                else:
                    strategy_backtest_results = strategy_backtest_results.append(backtest_result_df, ignore_index=True)

        logger.info("Ended backtesting on all currency.")

        # compute aggregated statistics for backtest runs on all currency pairs
        #self.mean_profit_percent = strategy_backtest_results["profit_percent"].mean()
        #self.mean_profit_percent_USDT = strategy_backtest_results["profit_percent_USDT"].mean()
        #self.mean_num_trades = strategy_backtest_results["num_trades"].mean()
        #self.mean_num_profitable_trade_pairs = strategy_backtest_results["num_profitable_trades"].mean()
        #self.mean_num_buys = strategy_backtest_results["num_buys"].mean()
        #self.mean_num_sells = strategy_backtest_results["num_sells"].mean()
        #self.mean_avg_profit_per_trade_pair = strategy_backtest_results["average_profit_percent_per_trade"].mean()
        #self.mean_buy_and_hold_profit_percent = strategy_backtest_results["profit_buy_and_hold_percent"].mean()
        #self.mean_buy_and_hold_profit_percent_USDT = strategy_backtest_results[
        #    "profit_buy_and_hold_percent_USDT"].mean()
        #self.mean_percent_gain_over_buy_and_hold = strategy_backtest_results["percent_gain_over_buy_and_hold"].mean()
        #self.mean_percent_gain_over_buy_and_hold_USDT = strategy_backtest_results["percent_gain_over_buy_and_hold_USDT"].mean()

        # for debugging
        # add mean and stdev columns to the dataframe (for debugging)
        strategy_backtest_results.loc["mean"] = strategy_backtest_results.mean(axis=0)
        strategy_backtest_results.loc["stdev"] = strategy_backtest_results.std(axis=0)

        writer = pd.ExcelWriter("backtest-{}-{}-{}.xlsx".format(self.strategy_class_name, self.start_timeframe, self.end_timeframe))
        strategy_backtest_results.to_excel(writer, 'Results')
        writer.save()

        # TODO: run the same for several-currency strategies

    def create_row_and_save(self, transaction_currency, counter_currency, resample_period, strategy_backtest_results):
        self.start_timeframe = self.start_timestamp
        self.end_timeframe = self.end_timestamp
        self.timestamp = self.end_timestamp
        self.transaction_currency = transaction_currency
        self.counter_currency = counter_currency
        self.resample_period = resample_period
        self.profit_percent = strategy_backtest_results["profit_percent"]
        self.profit_percent_USDT = strategy_backtest_results["profit_percent_USDT"]
        self.num_trades = strategy_backtest_results["num_trades"]
        self.num_profitable_trade_pairs = strategy_backtest_results["num_profitable_trades"]
        self.num_buys = strategy_backtest_results["num_buys"]
        self.num_sells = strategy_backtest_results["num_sells"]
        self.avg_profit_per_trade_pair = strategy_backtest_results["average_profit_percent_per_trade"]
        self.buy_and_hold_profit_percent = strategy_backtest_results["profit_buy_and_hold_percent"]
        self.buy_and_hold_profit_percent_USDT = strategy_backtest_results["profit_buy_and_hold_percent_USDT"]
        self.percent_gain_over_buy_and_hold = strategy_backtest_results["percent_gain_over_buy_and_hold"]
        self.percent_gain_over_buy_and_hold_USDT = strategy_backtest_results["percent_gain_over_buy_and_hold_USDT"]
        self.status = strategy_backtest_results["status"].value
        self.save()


    def run_backtest_portfolio(self):
        # allow holding several currencies at the same time (portfolio)
        pass

    # TODO: different transaction costs for different exchangers
    def simulate_trading(self, signals, start_cash, transaction_currency, counter_currency, start_timestamp,
                         end_timestamp, resample_period, source, transaction_cost_percent=0.0025):
        """
        Simulates trading with one currency based on signals.
        :param signals: a queryset of signals
        :param start_cash: starting amount of counter_currency
        :param transaction_currency: currency that we're buying
        :param counter_currency: our base currency
        :param start_timestamp: start of the time period that is being evaluated
        :param end_timestamp: end of the time period that is being evaluated
        :param resample_period: resample period (horizon)
        :param source: code of exchanger used
        :param transaction_cost_percent: exchanger fee per each trade
        :return: a dictionary with various stats if any trading takes place based on the signal list, None if the signal
                 list is empty or no trades get executed (for instance if only sell signals are in the list)
        """

        cash = start_cash   # the amount of counter_currency we have at any moment of trading
        crypto = 0          # the amount of transaction_currency we have at any moment of trading
        num_buys = 0        # total number of buys
        num_sells = 0       # total number of sells
        num_profitable_trades = 0   # total number of profitable trades (=number of sells for which we make a profit)
        invested_on_buy = 0         # the amount of cash spent on the last buy
        average_profit_percent_per_trade = 0    # average profit obtained by a buy-sell pair

        # convert start value to USDT (for performance statistics)
        start_cash_USDT = calculate_value_in_USDT(start_cash, start_timestamp,
                                                  counter_currency, source, resample_period)

        # store the time of the last trade
        last_trade_timestamp = None

        # simulate trading according to signals
        # we always spend all money to buy when a buy signal appears, and hold until the first sell signal
        for timestamp, signal in signals.items():
            last_trade_timestamp = timestamp  # storing the time of the last trade, needed for USDT conversion etc.

            price = get_price_at_timepoint(timestamp, source, transaction_currency, counter_currency, resample_period)
            if price is None or price == 0:
                logger.error("Unable to find or interpolate price data or price is zero - highly unlikely, please investigate!")
                continue  # covers a very rare case when we don't have price data and can't interpolate either

            if indicates_sell(signal) and crypto > 0 and invested_on_buy > 0:
                cash = cash + execute_sell(crypto, price, transaction_cost_percent)
                crypto = 0
                num_sells += 1

                # how much did we make on this buy - sell pair (in percent)
                buy_sell_pair_profit_percent = (invested_on_buy - cash) / invested_on_buy
                invested_on_buy = 0  # reset the invested amount for the trade pair
                average_profit_percent_per_trade += buy_sell_pair_profit_percent

                # check if the trade was profitable
                if buy_sell_pair_profit_percent > 0:
                    num_profitable_trades += 1

            elif indicates_buy(signal) and cash > 0:
                invested_on_buy += cash
                crypto = crypto + execute_buy(cash, price, transaction_cost_percent)
                cash = 0
                num_buys += 1

        num_trades = num_buys + num_sells

        # What if we didn't trade at all? Happens when no signals, or only sell signals.
        if num_trades == 0:
            return None

        # housekeeping in case that the last signal was a buy signal, meaning we didn't end up with cash but with crypto
        # calculate the value of this crypto in counter_currency to estimate profit
        if crypto > 0:
            price = get_price_at_timepoint(end_timestamp, source, transaction_currency,  # TODO what if no price data?
                                           counter_currency, resample_period)
            if price is None:
                end_cash = None
                end_cash_USDT = None
            else:
                end_cash = execute_sell(crypto, price, transaction_cost_percent)  # simulate selling at the end of timeframe
                end_cash_USDT = calculate_value_in_USDT(end_cash, end_timestamp, counter_currency, source, resample_period)
        else:
            end_cash = cash
            end_cash_USDT = calculate_value_in_USDT(end_cash, last_trade_timestamp.timestamp(),
                                                    counter_currency, source, resample_period)

        # calculate statistics
        if end_cash is not None:
            profit = end_cash - start_cash
            profit_percent = profit / start_cash
        else:
            profit = None
            profit_percent = None

        average_profit_percent_per_trade /= num_trades
        profit_buy_and_hold = calculate_profit_buy_and_hold(start_cash, source, transaction_currency, counter_currency,
                                                            resample_period, start_timestamp, end_timestamp,
                                                            transaction_cost_percent)
        if profit_buy_and_hold is not None and profit is not None:
            profit_buy_and_hold_percent = profit_buy_and_hold / start_cash
            percent_gain_over_buy_and_hold = profit_percent - profit_buy_and_hold_percent
        else:
            profit_buy_and_hold_percent = None
            percent_gain_over_buy_and_hold = None

        if end_cash_USDT is not None:
            profit_USDT = end_cash_USDT - start_cash_USDT
            profit_percent_USDT = profit_USDT / start_cash_USDT
        else:
            profit_USDT = None
            profit_percent_USDT = None

        if counter_currency == 2:  # if already trading in USDT
            profit_buy_and_hold_USDT = profit_buy_and_hold
        else:
            profit_buy_and_hold_USDT = calculate_profit_buy_and_hold_USDT(start_cash, source, transaction_currency,
                                                                          counter_currency, resample_period, start_timestamp,
                                                                          end_timestamp, transaction_cost_percent)
        if profit_buy_and_hold_USDT is not None:
            profit_buy_and_hold_percent_USDT = profit_buy_and_hold_USDT / start_cash_USDT
            percent_gain_over_buy_and_hold_USDT = profit_percent_USDT - profit_buy_and_hold_percent_USDT
        else:
            profit_buy_and_hold_percent_USDT = None
            percent_gain_over_buy_and_hold_USDT = None

        dict = {"transaction_currency": transaction_currency,
                "counter_currency": counter_currency,
                "source": source,
                "resample_period": resample_period,
                "profit": profit,
                "profit_percent": profit_percent,
                "profit_USDT": profit_USDT,
                "profit_percent_USDT": profit_percent_USDT,
                "num_buys": num_buys,
                "num_sells": num_sells,
                "num_trades": num_trades,
                "num_profitable_trades": num_profitable_trades,
                "average_profit_percent_per_trade": average_profit_percent_per_trade,
                "profit_buy_and_hold": profit_buy_and_hold,
                "profit_buy_and_hold_percent": profit_buy_and_hold_percent,
                "profit_buy_and_hold_USDT": profit_buy_and_hold_USDT,
                "profit_buy_and_hold_percent_USDT": profit_buy_and_hold_percent_USDT,
                "percent_gain_over_buy_and_hold": percent_gain_over_buy_and_hold,
                "percent_gain_over_buy_and_hold_USDT": percent_gain_over_buy_and_hold_USDT}
        status = BacktestStatus.PRICE_ERROR if None in dict.values() else BacktestStatus.OK
        dict["status"] = status
        return dict



# checks if a signal indicates sell
def indicates_sell(signal_name):
    if ALL_SIGNALS[signal_name].trend == -1:
        return True
    else:
        return False


# checks if a signal indicates buy
def indicates_buy(signal_name):
    if ALL_SIGNALS[signal_name].trend == 1:
        return True
    else:
        return False


# calculates how much currency we can buy for a given amount of cash and given the transaction costs
def execute_buy(cash_amount, unit_price, transaction_cost_percent):
    return cash_amount * (1 - transaction_cost_percent) / unit_price


# calculates how much we earn by selling a given amount of currency and given the transaction costs
def execute_sell(crypto_amount, unit_price, transaction_cost_percent):
    return crypto_amount * unit_price * (1 - transaction_cost_percent)


# calculates the profit if buying the currency on start_timeframe and selling on end_timeframe
def calculate_profit_buy_and_hold(cash, source, transaction_currency, counter_currency,
                                  resample_period, start_timeframe, end_timeframe, transaction_cost_percent):

    start_price = get_price_at_timepoint(datetime.utcfromtimestamp(start_timeframe),
                                         source, transaction_currency, counter_currency, resample_period)
    end_price = get_price_at_timepoint(datetime.utcfromtimestamp(end_timeframe),
                                       source, transaction_currency, counter_currency, resample_period)

    if start_price is None or end_price is None:
        return None

    # buying at the start of timeframe for all cash
    crypto = execute_buy(cash, start_price, transaction_cost_percent)

    # selling everything at the end of timeframe
    end_cash = execute_sell(crypto, end_price, transaction_cost_percent)

    return end_cash - cash


# calculates the profit if buying the currency on start_timeframe and selling on end_timeframe, in USDT
def calculate_profit_buy_and_hold_USDT(cash, source, transaction_currency, counter_currency,
                                  resample_period, start_timeframe, end_timeframe, transaction_cost_percent):

    if counter_currency == 2:
        return calculate_profit_buy_and_hold(cash, source, transaction_currency, counter_currency,
                                  resample_period, start_timeframe, end_timeframe, transaction_cost_percent)

    # convert cash value to USDT
    cash_USDT = calculate_value_in_USDT(cash, start_timeframe, counter_currency, source, resample_period)

    if cash_USDT is None:
        return None

    # buying at the start of timeframe for all cash
    start_price = get_price_at_timepoint(datetime.utcfromtimestamp(start_timeframe),
                                         source, transaction_currency, counter_currency, resample_period)

    if start_price is None:
        return None

    crypto = execute_buy(cash, start_price, transaction_cost_percent)

    # selling everything at the end of timeframe
    end_price = get_price_at_timepoint(datetime.utcfromtimestamp(end_timeframe),
                                       source, transaction_currency, counter_currency, resample_period)

    if end_price is None:
        return None

    end_cash = execute_sell(crypto, end_price, transaction_cost_percent)

    # convert end cash value to USDT
    end_cash_USDT = calculate_value_in_USDT(end_cash, end_timeframe, counter_currency, source, resample_period)

    if end_cash_USDT is None:
        return None

    return end_cash_USDT - cash_USDT


def calculate_value_in_USDT(amount, timestamp, counter_currency, source, resample_period):
    value = None
    if counter_currency == 2:   # trivial case, if the value is already in USDT
        return amount
    else:
        price_USDT = get_price_at_timepoint(timestamp=datetime.utcfromtimestamp(timestamp), source=source,
                                            transaction_currency=CURRENCY_NAMES[counter_currency],
                                            counter_currency=2, resample_period=resample_period)
        if price_USDT is not None:  # if no data for USDT price, None will be returned
            value = amount * price_USDT
    return value


def init_strategy(strategy_name, **kwargs):
    if strategy_name == "RsiSimpleStrategy":
        return RsiSimpleStrategy(**kwargs)
    elif strategy_name == "AnnSimpleStrategy":
        return AnnSimpleStrategy(**kwargs)
    elif strategy_name == "IchiKumoBreakoutStrategy":
        return IchiKumoBreakoutStrategy(**kwargs)


def get_all_currency_tuples():
    distinct = PriceResampl.objects.values("source", "transaction_currency", "counter_currency").distinct()
    return distinct


import logging
from apps.TA import TAException
from apps.TA.storages.abstract.timeseries_storage import TimeseriesStorage

logger = logging.getLogger(__name__)


class IndicatorException(TAException):
    pass


class TickerStorage(TimeseriesStorage):
    """
    stores timeseries data on tickers in a sorted set unique to each ticker and exchange
    todo: split the db by each exchange source
    """
    class_describer = "ticker"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.class_describer = kwargs.get('class_describer', self.__class__.class_describer)

        # 'ticker' REQUIRED
        # 'exchange EXPECTED BUT CAN STILL SAVE WITHOUT
        try:
            self.ticker = kwargs['ticker']  # str eg. BTC_USD
            self.exchange = str(kwargs.get('exchange', ""))  # str or int
        except KeyError:
            raise TAException("Indicator requires a ticker as initial parameter!")
        except Exception as e:
            raise TAException(str(e))
        else:
            if self.ticker.find("_") <= 0:
                raise TAException("ticker should be like BTC_USD")
            if not self.exchange:
                logger.debug("----- NO 'exchange' VALUE! ARE YOU SURE? -----")


    def get_db_key(self):
        self.db_key_prefix = f'{self.ticker}:{self.exchange}:'
        # by default will return "{ticker}:{exchange}:{class_name}"
        return super().get_db_key()


    @classmethod
    def query(cls, *args, **kwargs):

        ticker = kwargs.get("ticker", None)
        exchange = kwargs.get("exchange", None)
        if not ticker or not exchange:
            raise IndicatorException("ticker and exchange both requried for ticker query")
        kwargs["key_prefix"] = f'{ticker}:{exchange}'

        results_dict = super().query(*args, **kwargs)

        results_dict['exchange'] = exchange
        results_dict['ticker'] = ticker
        return results_dict
import logging
from datetime import datetime, timedelta

from apps.TA import PRICE_INDEXES, VOLUME_INDEXES, JAN_1_2017_TIMESTAMP
from apps.TA.storages.abstract.timeseries_storage import TimeseriesStorage
from apps.TA.storages.data.price import PriceStorage
from apps.TA.storages.data.volume import VolumeStorage
from apps.TA.storages.utils.list_search import missing_elements
from apps.TA.storages.utils.pv_resampling import generate_pv_storages
from apps.api.helpers import get_source_index, get_counter_currency_index
from apps.indicator.models import PriceHistory
from settings.redis_db import database

logger = logging.getLogger(__name__)


def find_start_score(ticker: str, exchange: str, index: str) -> float:
    """
    Find the score for the first value.
    To for informing data recovery because it's probably pointless
    to search for data before this starting score. Better to start at this
    score and then recover data from then up until now()

    :param ticker: eg. "ETH_BTC"
    :param exchange: eg. "binance"
    :param index: eg. "close_price"
    :return: the score as a float, eg. 148609.0
    """

    # eg. key = "ETH_BTC:binance:PriceStorage:close_price"
    key = f"{ticker}:{exchange}:PriceStorage:{index}"

    query_response = database.zrange(key, 0, 0)
    score = float(query_response[0].decode("utf-8").split(":")[1])
    return score


def find_pv_storage_data_gaps(ticker: str, exchange: str, index: str, back_to_the_backlog: bool = False) -> list:
    """
    Find and plug up gaps in the data for Price and Volume Storages

    :param ticker: eg. "ETH_BTC"
    :param exchange: eg. "binance"
    :param index: eg. "close_price", should be found in TA.PRICE_INDEXES or TA.VOLUME_INDEXES
    :param start_score: optional, default is jan_1_2017
    :param end_score: optional, default will reset to 2 hours ago from now()
    :return: list of scores that are still missing gaps, [] empty list means no gaps
    """
    from apps.TA.management.commands.TA_restore import save_pv_histories_to_redis

    # validate index and determine storage class
    if index in PRICE_INDEXES:
        storage_class = PriceStorage
    elif index in VOLUME_INDEXES:
        storage_class = VolumeStorage
    else:
        raise Exception("unknown index")

    storage_instance = storage_class(ticker=ticker, exchange=exchange, index=index, timestamp=JAN_1_2017_TIMESTAMP)
    redis_zset_withscores = database.zrange(storage_instance.get_db_key(), 0, -1, withscores=True)

    start_score = int(TimeseriesStorage.score_from_timestamp(datetime(2018,12,11).timestamp()))  # todo: change to 2018,1,1
    end_score = int(TimeseriesStorage.score_from_timestamp(datetime.now().timestamp()))  # 206836 is Dec 20

    scores = [int(score) for (value, score) in redis_zset_withscores if score > start_score]
    scores.insert(0,start_score)
    scores.append(end_score+1)

    missing_scores = missing_elements(scores)

    restored_scores = []

    # if back_to_the_backlog:
    #     # let's go "back to the backlog"; try to reach back and deep into the SQL
    #     restorable_scores = []
    #
    #     for processing_score in missing_scores:
    #         processing_datetime = TimeseriesStorage.datetime_from_score(processing_score)
    #
    #         price_history_objects = PriceHistory.objects.filter(
    #             timestamp__gte=processing_datetime - timedelta(minutes=1),
    #             timestamp__lte=processing_datetime,
    #             source=get_source_index(exchange),
    #             counter_currency=get_counter_currency_index(ticker.split("_")[1])
    #         )
    #
    #         for ph_object in price_history_objects:
    #             results = save_pv_histories_to_redis(ph_object)
    #             if sum(results):
    #                 restorable_scores.append(processing_score)
    #
    #     if len(restorable_scores):
    #         logger.debug("successfully restored missing data from SQL into PriceVolumeHistoryStorage")

    for processing_score in missing_scores:
        if generate_pv_storages(ticker, exchange, index, processing_score):
            restored_scores.append(processing_score)
            continue  # problem solved!

    missing_scores = set(missing_scores) - set(restored_scores)

    if len(restored_scores):
        logger.debug(f"successfully restored {len(restored_scores)} scores from PriceVolumeHistoryStorage")

    if len(missing_scores):
        logger.debug(f"there are {len(missing_scores)} mores scores not yet restored")

    return list(missing_scores - set(restored_scores))


def force_plug_pv_storage_data_gaps(ticker: str, exchange: str, index: str, scores: list = []):
    # validate index and determine storage class
    if index in PRICE_INDEXES:
        storage_class = PriceStorage
    elif index in VOLUME_INDEXES:
        storage_class = VolumeStorage
        return  # todo: turn this back on later
    else:
        raise Exception("unknown index")

    for missing_score in scores:
        logger.debug(f"working with {missing_score} == timestamp {TimeseriesStorage.timestamp_from_score(missing_score)}")

        query_response = storage_class.query(
            ticker=ticker,
            exchange=exchange,
            index=index,
            timestamp=TimeseriesStorage.timestamp_from_score(missing_score),
            timestamp_tolerance=0,
            periods_range=5
        )

        if not len(query_response['values']):
            # no previous value to copy
            continue

        if missing_score == int(float(query_response['scores'][-1])):
            # value is not actaully missing, skip
            continue

        copied_value = int(query_response['values'][-1])
        copied_score = float(query_response['scores'][-1])


        logger.debug("printing query response >>>")
        logger.debug(query_response)

        assert 'warning' in query_response
        assert float(query_response['earliest_timestamp']) <= float(query_response['latest_timestamp'])
        assert float(query_response['latest_timestamp']) <= TimeseriesStorage.timestamp_from_score(missing_score - 1)
        assert copied_score <= missing_score - 1

        storage = storage_class(ticker=ticker,
                                exchange=exchange,
                                timestamp=TimeseriesStorage.timestamp_from_score(missing_score),
                                index=index)

        # save value equal to previous score's value
        storage.value = copied_value
        storage.save(publish=True)
        logger.debug("Filled the gap on score " + str(missing_score))


def test_force_plug_pv_storage_data_gaps():
    ticker = "ETH_BTC"
    exchange = "binance"
    index = "close_price"
    key = f"{ticker}:{exchange}:PriceStorage:{index}"
    database.zremrangebyscore(key, 155773 + 1, 155773 + 2)

    scores = [155773, 155773 + 1, 155773 + 2]

    force_plug_pv_storage_data_gaps(ticker, exchange, index, scores)

    database.zremrangebyscore(key, 155773 + 1, 155773 + 2)

# exmaple query with missing data
# key = "ETH_BTC:binance:PriceStorage:close_price"
# db.zrange(key, -20, -1, withscores=True)
# [(b'7337200:155773.0', 155773.0),
#  (b'7389999:155785.0', 155785.0),
#  (b'7380700:155797.0', 155797.0),
#  (b'7368200:155809.0', 155809.0),
#  (b'7118600:156049.0', 156049.0),
#  (b'4019799:175105.0', 175105.0),
#  (b'4023500:175106.0', 175106.0),
#  (b'4021099:175107.0', 175107.0),
#  (b'4020700:175108.0', 175108.0),
#  (b'4031599:175117.0', 175117.0),
#  (b'4033000:175129.0', 175129.0)]

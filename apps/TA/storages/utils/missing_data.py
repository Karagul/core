import logging
from datetime import datetime, timedelta

from apps.TA import PRICE_INDEXES, VOLUME_INDEXES
from apps.TA.management.commands.TA_restore import save_pv_histories_to_redis
from apps.TA.storages.abstract.timeseries_storage import TimeseriesStorage
from apps.TA.storages.data.price import PriceStorage
from apps.TA.storages.data.pv_history import PriceVolumeHistoryStorage
from apps.TA.storages.data.volume import VolumeStorage
from apps.TA.storages.utils.pv_resampling import generate_pv_storages
from apps.api.helpers import get_source_index, get_counter_currency_index
from apps.indicator.models import PriceHistory


logger = logging.getLogger(__name__)


def find_start_score(ticker: str, exchange: str, index: str) -> int:

    score = 0



    return int(score)


def find_pv_storage_data_gaps(ticker: str, exchange: str, index: str, start_score: float = 0, end_score: float = 0) -> list:
    """
    Find and plug up gaps in the data for Price and Volume Storages
    :param ticker: eg. "ETH_BTC"
    :param exchange: eg. "binance"
    :param index: eg. "close_price", should be found in TA.PRICE_INDEXES or TA.VOLUME_INDEXES
    :param start_score: optional, default is jan_1_2017
    :param end_score: optional, default will reset to 2 hours ago from now()
    :return: list of scores that are still missing gaps, [] empty list means no gaps
    """

    # validate index and determine storage class
    if index in PRICE_INDEXES:
        storage_class = PriceStorage
    elif index in VOLUME_INDEXES:
        storage_class = VolumeStorage
    else:
        raise Exception("unknown index")

    # set score range for processing
    start_score = start_score or 0
    end_score = end_score or TimeseriesStorage.score_from_timestamp((datetime.today()-timedelta(hours=2)).timestamp())
    processing_score = start_score

    missing_scores = []
    dont_repeat_this_score = 0

    while processing_score < end_score:
        processing_score += 1

        query_response = storage_class.query(
            ticker=ticker,
            exchange=exchange,
            index=index,
            timestamp=TimeseriesStorage.timestamp_from_score(processing_score),
            timestamp_tolerance=0,
            periods_range=0
        )
        # there ought to be a single value here. if missing, try to fill the gap

        if query_response['values_count']:
            continue  # no missing data, all is groovy, move along

        if generate_pv_storages(ticker, exchange, index, processing_score):
            logger.debug("successfully restored from PriceVolumeHistoryStorage")
            continue  # problem solved!

        # still here? well damn, we have big hole in the data
        if dont_repeat_this_score == processing_score: # we dont' want to try this more than once
            missing_scores.append(processing_score)
            continue  # we give up on this score :(

        else:
            # let's go "back to the backlog"; try to reach back and deep into the SQL
            dont_repeat_this_score = processing_score

        processing_datetime = TimeseriesStorage.datetime_from_score(processing_score)

        price_history_objects = PriceHistory.objects.filter(
            timestamp__gte=processing_datetime - timedelta(minutes=1),
            timestamp__lte=processing_datetime,
            source=get_source_index(exchange),
            counter_currency=get_counter_currency_index(ticker.split("_")[1])
        )

        new_datapoints_saved = 0
        for ph_object in price_history_objects:
            results = save_pv_histories_to_redis(ph_object)
            new_datapoints_saved += sum(results)

        if new_datapoints_saved > 0:
            logger.debug("successfully restored missing data from SQL into PriceVolumeHistoryStorage")
            # go back and try this score again
            processing_score -= 1

    logger.debug("finished with missing scores: " + str(missing_scores))
    return missing_scores


def force_plug_pv_storage_data_gaps(ticker: str, exchange: str, index: str, scores: list =[]):

    # validate index and determine storage class
    if index in PRICE_INDEXES:
        storage_class = PriceStorage
    elif index in VOLUME_INDEXES:
        storage_class = VolumeStorage
    else:
        raise Exception("unknown index")

    for score in scores:

        query_response = storage_class.query(
            ticker=ticker,
            exchange=exchange,
            index=index,
            timestamp=TimeseriesStorage.timestamp_from_score(score),
            timestamp_tolerance=0,
            periods_range=1
        )

        if query_response['values_count'] > 0 and score == float(query_response['scores'][-1]):
            #value is not missing
            continue


        q_value = int(query_response['values'][0])
        q_score = float(query_response['scores'][0])


        logger.debug(f"working with {score} == timestamp {TimeseriesStorage.timestamp_from_score(score)}")
        logger.debug("printing query response >>>")
        logger.debug(query_response)

        assert float(query_response['earliest_timestamp']) == float(query_response['latest_timestamp'])
        assert float(query_response['latest_timestamp']) == TimeseriesStorage.timestamp_from_score(score-1)
        assert q_score == score - 1

        storage = storage_class(ticker=ticker,
                                exchange=exchange,
                                timestamp=TimeseriesStorage.timestamp_from_score(score),
                                index=index)

        # save value equal to previous score's value
        storage.value = q_value
        storage.save()
        logger.debug("Filled the gap on score " + str(score))



def test_force_plug_pv_storage_data_gaps():
    from settings.redis_db import database

    ticker = "ETH_BTC"
    exchange = "binance"
    index = "close_price"
    key = f"{ticker}:{exchange}:PriceStorage:{index}"
    database.zremrangebyscore(key, 155773 + 1, 155773 + 2)

    scores = [155773, 155773+1, 155773+2]

    force_plug_pv_storage_data_gaps(ticker, exchange, index, scores)
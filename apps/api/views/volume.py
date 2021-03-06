from rest_framework import exceptions
from rest_framework.generics import ListAPIView

from apps.api.serializers import VolumeSerializer
from apps.api.paginations import StandardResultsSetPagination

from apps.api.helpers import filter_queryset_by_timestamp_history

# Volume
class ListVolumes(ListAPIView):
    """Return list of price volumes.

    When startdate is not set, API return records for the last month.

    /api/v2/volumes/

    URL query parameters

    For filtering

        transaction_currency -- string 'BTC', 'ETH' etc
        counter_currency -- number 0=BTC, 1=ETH, 2=USDT, 3=XMR
        source -- number 0=poloniex, 1=bittrex, 2=binance
        startdate -- from this date (inclusive). Example 2018-02-12T09:09:15
        enddate -- to this date (inclusive)

    For pagination

        cursor - indicator that the client may use to page through the result set
        page_size -- a numeric value indicating the page size

    Examples

        /api/v2/volumes/?transaction_currency=ETH&counter_currency=0&startdate=2018-02-10T22:14:37&enddate=2018-02-10T22:27:58
    """

    serializer_class = VolumeSerializer
    pagination_class = StandardResultsSetPagination

    filter_fields = ('transaction_currency', 'counter_currency', 'source')

    model = serializer_class.Meta.model

    def get_queryset(self):
    # check required parameters
        for param in ('source', 'transaction_currency', 'counter_currency'):
            if param not in self.request.query_params:
                raise exceptions.NotFound(detail=f"Missing required parameter: {param}")

        queryset = filter_queryset_by_timestamp_history(self)
        return queryset

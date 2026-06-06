"""GET /v1/stats/export/ — download daily stats as a CSV file."""
import logging
from datetime import date, timedelta

from django.http import HttpResponse
from django.utils.dateparse import parse_date
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.views import APIView

from services.analytics_service import export_stats_csv

logger = logging.getLogger(__name__)

_DATE_FROM_PARAM = OpenApiParameter('date_from', str, description='ISO 8601 start date', required=False)
_DATE_TO_PARAM = OpenApiParameter('date_to', str, description='ISO 8601 end date', required=False)
_DATE_RANGE_PARAM = OpenApiParameter(
    'date_range', str,
    description='Shorthand range: 7d | 30d | 90d (overrides date_from/date_to)',
    required=False,
)
_STREAM_PARAM = OpenApiParameter('stream', str, description='Filter by stream slug', required=False)

_RANGE_MAP = {'7d': 6, '30d': 29, '90d': 89}


@extend_schema(
    parameters=[_DATE_FROM_PARAM, _DATE_TO_PARAM, _DATE_RANGE_PARAM, _STREAM_PARAM],
    responses={200: {'type': 'string', 'format': 'binary'}},
    summary='Export daily stats as CSV',
    tags=['Analytics'],
)
class StatsExportView(APIView):
    def get(self, request) -> HttpResponse:
        today = date.today()
        stream = request.query_params.get('stream')

        date_range = request.query_params.get('date_range')
        if date_range and date_range in _RANGE_MAP:
            date_from = today - timedelta(days=_RANGE_MAP[date_range])
            date_to = today
        else:
            raw_from = request.query_params.get('date_from')
            raw_to = request.query_params.get('date_to')
            date_from = parse_date(raw_from) if raw_from else today - timedelta(days=6)
            date_to = parse_date(raw_to) if raw_to else today

        if not date_from or not date_to or date_from > date_to:
            return HttpResponse('Invalid date range.', status=400, content_type='text/plain')

        csv_content = export_stats_csv(request.user, date_from, date_to, stream)
        filename = f'stats_{date_from}_{date_to}.csv'
        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

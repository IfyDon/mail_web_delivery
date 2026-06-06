"""GET /v1/stats — per-day breakdown of email events for a date range."""
import logging
from datetime import date, timedelta

from django.utils.dateparse import parse_date
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.email_messages.models import Message
from apps.events.models import Event

logger = logging.getLogger(__name__)

_DATE_FROM_PARAM = OpenApiParameter(
    "date_from", str, description="ISO 8601 start date", required=False
)
_DATE_TO_PARAM = OpenApiParameter(
    "date_to", str, description="ISO 8601 end date", required=False
)
_DATE_RANGE_PARAM = OpenApiParameter(
    "date_range", str,
    description="Shorthand range: 7d | 30d | 90d (overrides date_from/date_to)",
    required=False,
)
_STREAM_PARAM = OpenApiParameter(
    "stream", str, description="Filter by stream slug", required=False
)

_RANGE_MAP = {"7d": 6, "30d": 29, "90d": 89}

_EVENT_TYPE_MAP = {
    Event.TYPE_DELIVERED: "delivered",
    Event.TYPE_OPEN:      "opened",
    Event.TYPE_CLICK:     "clicked",
    Event.TYPE_BOUNCE:    "bounced",
    Event.TYPE_COMPLAINT: "complained",
}

_ZERO_DAY = lambda: {  # noqa: E731
    "sent": 0, "delivered": 0, "opened": 0,
    "clicked": 0, "bounced": 0, "complained": 0,
}


def _sum_days(by_day: dict) -> dict:
    totals = _ZERO_DAY()
    for day_data in by_day.values():
        for key in totals:
            totals[key] += day_data[key]
    return totals


@extend_schema(
    parameters=[_DATE_FROM_PARAM, _DATE_TO_PARAM, _DATE_RANGE_PARAM, _STREAM_PARAM],
    responses={200: {"type": "object"}},
    summary="Aggregated email stats (per-day breakdown)",
    tags=["Analytics"],
)
class StatsView(APIView):
    def get(self, request):
        today = date.today()
        stream = request.query_params.get("stream")

        # date_range shorthand takes priority over explicit date_from/date_to
        date_range = request.query_params.get("date_range")
        if date_range and date_range in _RANGE_MAP:
            date_from = today - timedelta(days=_RANGE_MAP[date_range])
            date_to = today
        else:
            raw_from = request.query_params.get("date_from")
            raw_to = request.query_params.get("date_to")
            date_from = parse_date(raw_from) if raw_from else today - timedelta(days=6)
            date_to = parse_date(raw_to) if raw_to else today

        if not date_from or not date_to or date_from > date_to:
            return Response(
                {"status": "error", "code": 400, "errors": [
                    {"field": "date_from", "message": "Invalid or reversed date range."}
                ]},
                status=400,
            )

        # Try pre-aggregated DailyStats first (fast path)
        try:
            from apps.analytics.models import DailyStats
            qs = DailyStats.objects.filter(
                user=request.user,
                date__gte=date_from,
                date__lte=date_to,
            )
            if stream:
                qs = qs.filter(stream=stream)

            # Build by_day dict from pre-aggregated rows
            by_day: dict = {}
            cursor = date_from
            while cursor <= date_to:
                by_day[cursor.isoformat()] = _ZERO_DAY()
                cursor += timedelta(days=1)

            for row in qs.values(
                'date', 'sent', 'delivered', 'opened', 'clicked', 'bounced', 'complained'
            ):
                d = row['date'].isoformat()
                if d in by_day:
                    for key in ('sent', 'delivered', 'opened', 'clicked', 'bounced', 'complained'):
                        by_day[d][key] = row[key]

            # If DailyStats has no rows yet, fall through to live query
            if not qs.exists():
                raise LookupError("no aggregated data yet")

        except Exception:  # noqa: BLE001 — fall back to live Event query
            by_day = {}
            cursor = date_from
            while cursor <= date_to:
                by_day[cursor.isoformat()] = _ZERO_DAY()
                cursor += timedelta(days=1)

            msg_qs = Message.objects.filter(
                user=request.user,
                created_at__date__gte=date_from,
                created_at__date__lte=date_to,
            )
            if stream:
                msg_qs = msg_qs.filter(stream=stream)
            for msg in msg_qs.values("created_at__date"):
                d = msg["created_at__date"].isoformat()
                if d in by_day:
                    by_day[d]["sent"] += 1

            event_qs = Event.objects.filter(
                message__user=request.user,
                timestamp__date__gte=date_from,
                timestamp__date__lte=date_to,
                type__in=list(_EVENT_TYPE_MAP.keys()),
            )
            if stream:
                event_qs = event_qs.filter(message__stream=stream)
            for ev in event_qs.values("type", "timestamp__date"):
                d = ev["timestamp__date"].isoformat()
                key = _EVENT_TYPE_MAP.get(ev["type"])
                if d in by_day and key:
                    by_day[d][key] += 1

        totals = _sum_days(by_day)
        # Return field as "daily" — matches frontend expectation
        daily = [{"date": d, **stats} for d, stats in sorted(by_day.items())]

        sent = totals.get("sent", 0)
        bounce_rate = round(totals.get("bounced", 0) / sent * 100, 2) if sent > 0 else 0.0
        complaint_rate = round(totals.get("complained", 0) / sent * 100, 2) if sent > 0 else 0.0

        return Response({
            "date_from":      date_from.isoformat(),
            "date_to":        date_to.isoformat(),
            "date_range":     date_range,
            "stream":         stream,
            "totals":         totals,
            "daily":          daily,
            "bounce_rate":    bounce_rate,
            "complaint_rate": complaint_rate,
        })

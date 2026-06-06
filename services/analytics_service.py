"""Analytics service: query aggregated stats and produce CSV exports."""
import csv
import io
from datetime import date, timedelta

from apps.analytics.models import DailyStats
from apps.email_messages.models import Message
from apps.events.models import Event

_STAT_KEYS = ('sent', 'delivered', 'opened', 'clicked', 'bounced', 'complained')

_EVENT_TYPE_MAP = {
    Event.TYPE_DELIVERED: 'delivered',
    Event.TYPE_OPEN:      'opened',
    Event.TYPE_CLICK:     'clicked',
    Event.TYPE_BOUNCE:    'bounced',
    Event.TYPE_COMPLAINT: 'complained',
}


def _zero_day() -> dict:
    return {k: 0 for k in _STAT_KEYS}


def get_daily_stats(
    user,
    date_from: date,
    date_to: date,
    stream: str | None = None,
) -> list[dict]:
    """Return a list of per-day stat dicts ordered by date.

    Tries the pre-aggregated DailyStats table first; falls back to a live
    query on Message + Event if no aggregated rows exist for the range.
    """
    day_count = (date_to - date_from).days + 1
    by_day: dict[str, dict] = {
        (date_from + timedelta(days=i)).isoformat(): _zero_day()
        for i in range(day_count)
    }

    qs = DailyStats.objects.filter(
        user=user, date__gte=date_from, date__lte=date_to,
    )
    if stream:
        qs = qs.filter(stream=stream)

    if qs.exists():
        for row in qs.values('date', *_STAT_KEYS):
            d = row['date'].isoformat()
            if d in by_day:
                for k in _STAT_KEYS:
                    by_day[d][k] = row[k]
    else:
        # Live fallback: count from raw Message + Event tables
        msg_qs = Message.objects.filter(
            user=user,
            created_at__date__gte=date_from,
            created_at__date__lte=date_to,
        )
        if stream:
            msg_qs = msg_qs.filter(stream=stream)
        for msg in msg_qs.values('created_at__date'):
            d = msg['created_at__date'].isoformat()
            if d in by_day:
                by_day[d]['sent'] += 1

        event_qs = Event.objects.filter(
            message__user=user,
            timestamp__date__gte=date_from,
            timestamp__date__lte=date_to,
            type__in=list(_EVENT_TYPE_MAP),
        )
        if stream:
            event_qs = event_qs.filter(message__stream=stream)
        for ev in event_qs.values('type', 'timestamp__date'):
            d = ev['timestamp__date'].isoformat()
            key = _EVENT_TYPE_MAP.get(ev['type'])
            if d in by_day and key:
                by_day[d][key] += 1

    return [{'date': d, **stats} for d, stats in sorted(by_day.items())]


def get_totals(daily: list[dict]) -> dict:
    """Sum each stat key across all daily rows and return a single totals dict."""
    totals = _zero_day()
    for day in daily:
        for k in _STAT_KEYS:
            totals[k] += day[k]
    return totals


def export_stats_csv(
    user,
    date_from: date,
    date_to: date,
    stream: str | None = None,
) -> str:
    """Return a CSV string of daily stats suitable for file download."""
    daily = get_daily_stats(user, date_from, date_to, stream)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=['date', *_STAT_KEYS])
    writer.writeheader()
    writer.writerows(daily)
    return buf.getvalue()

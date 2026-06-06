"""Roll up Event rows into DailyStats — called by the Celery Beat task."""
from datetime import date

from django.db.models import Count

from apps.analytics.models import DailyStats
from apps.email_messages.models import Message
from apps.events.models import Event


def rollup_day(target: date) -> int:
    """Aggregate all events for *target* date into DailyStats rows.

    Uses update_or_create so it is safe to re-run for the same date.
    Returns the number of users processed.
    """
    user_ids = list(
        Message.objects
        .filter(created_at__date=target)
        .values_list('user_id', flat=True)
        .distinct()
    )

    for user_id in user_ids:
        sent = Message.objects.filter(
            user_id=user_id, created_at__date=target
        ).count()

        event_counts = {
            row['type']: row['cnt']
            for row in (
                Event.objects
                .filter(message__user_id=user_id, timestamp__date=target)
                .values('type')
                .annotate(cnt=Count('id'))
            )
        }

        DailyStats.objects.update_or_create(
            user_id=user_id,
            date=target,
            stream='',
            defaults={
                'sent': sent,
                'delivered': event_counts.get(Event.TYPE_DELIVERED, 0),
                'opened': event_counts.get(Event.TYPE_OPEN, 0),
                'clicked': event_counts.get(Event.TYPE_CLICK, 0),
                'bounced': event_counts.get(Event.TYPE_BOUNCE, 0),
                'complained': event_counts.get(Event.TYPE_COMPLAINT, 0),
            },
        )

    return len(user_ids)

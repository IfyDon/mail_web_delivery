"""Periodic maintenance tasks: purge old events, expire old tokens."""
import logging

from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)

_EVENT_RETENTION_DAYS   = 90   # keep events for 90 days
_MESSAGE_RETENTION_DAYS = 45   # keep delivered/suppressed messages for 45 days


@shared_task
def cleanup_old_events() -> dict:
    """Delete Event rows older than EVENT_RETENTION_DAYS and archive old Messages."""
    from apps.events.models import Event
    from apps.email_messages.models import Message
    from django.conf import settings

    event_cutoff   = timezone.now() - timedelta(
        days=getattr(settings, 'EVENT_RETENTION_DAYS', _EVENT_RETENTION_DAYS)
    )
    message_cutoff = timezone.now() - timedelta(
        days=getattr(settings, 'MESSAGE_RETENTION_DAYS', _MESSAGE_RETENTION_DAYS)
    )

    events_deleted, _ = Event.objects.filter(timestamp__lt=event_cutoff).delete()
    messages_deleted, _ = Message.objects.filter(
        created_at__lt=message_cutoff,
        status__in=[
            Message.STATUS_DELIVERED,
            Message.STATUS_SUPPRESSED,
            Message.STATUS_CANCELLED,
        ],
    ).delete()

    logger.info(
        'cleanup_old_events: deleted %d events, %d messages',
        events_deleted,
        messages_deleted,
    )
    return {'events_deleted': events_deleted, 'messages_deleted': messages_deleted}

"""Re-queue messages that are stuck in 'queued' status for more than STUCK_THRESHOLD minutes."""
import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

_STUCK_THRESHOLD_MINUTES = 60


@shared_task
def retry_stuck_messages() -> dict:
    """Find messages stuck in queued status and re-enqueue them."""
    from apps.email_messages.models import Message
    from services.email_service import queue_email
    from django.conf import settings

    threshold = getattr(settings, 'STUCK_MESSAGE_THRESHOLD_MINUTES', _STUCK_THRESHOLD_MINUTES)
    cutoff = timezone.now() - timedelta(minutes=threshold)

    stuck = Message.objects.filter(
        status=Message.STATUS_QUEUED,
        updated_at__lt=cutoff,
    ).values_list('pk', flat=True)[:100]  # process at most 100 at a time

    count = 0
    for message_id in stuck:
        try:
            queue_email(str(message_id))
            count += 1
        except Exception:
            logger.exception('retry_stuck_messages: failed to re-queue %s', message_id)

    if count:
        logger.info('retry_stuck_messages: re-queued %d stuck messages', count)
    return {'requeued': count}

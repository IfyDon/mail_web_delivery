"""Celery task: dispatch messages whose scheduled_at time has arrived.

Runs every minute via Celery Beat. Safe to run concurrently — uses
select_for_update(skip_locked=True) so multiple workers never double-dispatch
the same message.
"""

import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def dispatch_scheduled_messages() -> dict:
    """Pick up all scheduled messages due for delivery and enqueue send_email_task."""
    from apps.email_messages.models import Message
    from workers.tasks.send_email import send_email_task

    now = timezone.now()
    dispatched = []

    with transaction.atomic():
        due = (
            Message.objects.select_for_update(skip_locked=True)
            .filter(status=Message.STATUS_SCHEDULED, scheduled_at__lte=now)
        )
        for msg in due:
            msg.status = Message.STATUS_QUEUED
            msg.save(update_fields=['status', 'updated_at'])
            dispatched.append(str(msg.pk))

    for message_id in dispatched:
        send_email_task.delay(message_id)
        logger.info('dispatch_scheduled: enqueued %s', message_id)

    return {'dispatched': len(dispatched), 'at': now.isoformat()}

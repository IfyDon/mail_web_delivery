"""Webhook service: build event payloads and fan out to subscriber endpoints."""

import logging

from django.utils import timezone

logger = logging.getLogger(__name__)


def build_event_payload(
    event_type: str,
    message_id: str = '',
    metadata: dict = None,
) -> dict:
    """Return a standardised event payload dict for webhook delivery."""
    return {
        'event_type': event_type,
        'message_id': message_id,
        'timestamp': timezone.now().isoformat(),
        'metadata': metadata or {},
    }


def trigger_webhooks(user, event_type: str, payload: dict) -> int:
    """Enqueue dispatch tasks for every active webhook subscribed to event_type.

    Returns the number of tasks enqueued.
    """
    from apps.webhooks.models import Webhook, WebhookDispatchLog
    from workers.tasks.webhook_dispatch import dispatch_webhook_task

    webhooks = (
        Webhook.objects
        .filter(user=user, is_active=True)
        .only('id', 'url', 'secret', 'event_types')
    )

    enqueued = 0
    for webhook in webhooks:
        if not webhook.listens_to(event_type):
            continue

        log = WebhookDispatchLog.objects.create(
            webhook=webhook,
            event_type=event_type,
            payload=payload,
        )
        dispatch_webhook_task.delay(webhook.pk, log.pk, payload)
        enqueued += 1
        logger.debug(
            'trigger_webhooks: enqueued log=%s webhook=%s event=%s',
            log.pk, webhook.pk, event_type,
        )

    return enqueued

"""
Celery task: scan per-user bounce rates over the last 24 h.
Any account whose bounce rate exceeds BOUNCE_RATE_THRESHOLD (10 %) with at least
MIN_SAMPLE_SIZE sends has sending_paused set to True and receives a webhook event.
Mirrors Postmark's policy of suspending senders that breach the 10 % threshold.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

BOUNCE_RATE_THRESHOLD = 0.10   # 10 % — matches Postmark's suspension threshold
MIN_SAMPLE_SIZE = 50            # Ignore accounts with fewer sends (avoid false positives)


@shared_task
def check_bounce_rates() -> dict:
    """Pause sending for users whose 24-h bounce rate exceeds BOUNCE_RATE_THRESHOLD."""
    from django.contrib.auth import get_user_model
    from apps.email_messages.models import Message
    from apps.events.models import Event

    User = get_user_model()
    since = timezone.now() - timedelta(hours=24)
    checked = paused = 0

    for user in User.objects.filter(sending_paused=False).iterator():
        sent_ids = list(
            Message.objects.filter(
                user=user,
                status__in=(Message.STATUS_SENT, Message.STATUS_DELIVERED),
                updated_at__gte=since,
            ).values_list('id', flat=True)
        )
        total_sent = len(sent_ids)
        if total_sent < MIN_SAMPLE_SIZE:
            continue

        bounce_count = Event.objects.filter(
            message_id__in=sent_ids,
            type=Event.TYPE_BOUNCE,
            timestamp__gte=since,
        ).count()

        checked += 1
        bounce_rate = bounce_count / total_sent

        if bounce_rate > BOUNCE_RATE_THRESHOLD:
            User.objects.filter(pk=user.pk).update(sending_paused=True)
            logger.warning(
                'check_bounce_rates: paused user=%s bounce_rate=%.1f%% (%d/%d)',
                user.pk, bounce_rate * 100, bounce_count, total_sent,
            )
            _fire_pause_webhook(user, bounce_rate, bounce_count, total_sent)
            paused += 1

    logger.info('check_bounce_rates: checked=%d paused=%d', checked, paused)
    return {'checked': checked, 'paused': paused}


def _fire_pause_webhook(user, bounce_rate: float, bounce_count: int, total_sent: int) -> None:
    try:
        from services.webhook_service import build_event_payload, trigger_webhooks
        payload = build_event_payload('sending_paused', str(user.pk), {
            'bounce_rate': round(bounce_rate, 4),
            'bounce_count': bounce_count,
            'total_sent': total_sent,
            'reason': 'bounce_rate_threshold_exceeded',
        })
        trigger_webhooks(user, 'sending_paused', payload)
    except Exception:
        logger.exception('check_bounce_rates: webhook failed for user %s', user.pk)

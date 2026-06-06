"""Celery task: sign and POST a webhook payload, log each attempt, retry on failure."""

import hashlib
import hmac
import json
import logging

import requests
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.utils import timezone

logger = logging.getLogger(__name__)

# Exponential backoff (seconds): 1m, 5m, 15m, 30m, 1h, then 2h × remaining
_RETRY_DELAYS = [60, 300, 900, 1800, 3600, 7200, 7200, 7200, 7200, 7200]


@shared_task(bind=True, max_retries=10, acks_late=True)
def dispatch_webhook_task(self, webhook_id: int, log_id: int, payload: dict) -> dict:
    """POST a webhook payload to the user's endpoint with HMAC-SHA256 signature.

    Updates WebhookDispatchLog on every attempt. Retries up to 10 times
    with exponential backoff on network errors or non-2xx responses.
    """
    from apps.webhooks.models import Webhook, WebhookDispatchLog

    try:
        webhook = Webhook.objects.get(pk=webhook_id, is_active=True)
    except Webhook.DoesNotExist:
        logger.warning('dispatch_webhook_task: webhook %s not found or inactive', webhook_id)
        return {'status': 'skipped', 'reason': 'webhook_not_found'}

    try:
        log = WebhookDispatchLog.objects.get(pk=log_id)
    except WebhookDispatchLog.DoesNotExist:
        logger.error('dispatch_webhook_task: log %s not found', log_id)
        return {'status': 'error', 'reason': 'log_not_found'}

    # Serialize payload deterministically for signing
    body = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()

    # HMAC-SHA256 signature (same convention as GitHub webhooks)
    sig = hmac.new(webhook.secret.encode(), body, hashlib.sha256).hexdigest()

    headers = {
        'Content-Type': 'application/json',
        'X-WebMail-Signature': f'sha256={sig}',
        'X-WebMail-Event': str(payload.get('event_type', '')),
        'X-WebMail-Delivery': str(log_id),
    }

    # Attempt the POST
    try:
        resp = requests.post(webhook.url, data=body, headers=headers, timeout=10)
    except requests.RequestException as exc:
        logger.warning(
            'dispatch_webhook_task: network error for log=%s attempt=%d: %s',
            log_id, log.attempts + 1, exc,
        )
        log.attempts += 1
        log.last_attempted_at = timezone.now()
        log.save(update_fields=['attempts', 'last_attempted_at'])
        return _retry_or_give_up(self, log, exc)

    # Record the attempt
    log.response_status = resp.status_code
    log.response_body = resp.text[:2048]
    log.attempts += 1
    log.last_attempted_at = timezone.now()

    if resp.status_code in (200, 201, 202, 204):
        log.succeeded = True
        log.save(update_fields=[
            'response_status', 'response_body', 'attempts', 'succeeded', 'last_attempted_at',
        ])
        logger.info(
            'dispatch_webhook_task: delivered log=%s to %s (HTTP %s)',
            log_id, webhook.url[:60], resp.status_code,
        )
        return {'status': 'delivered', 'http_status': resp.status_code}

    # Non-2xx — save progress then retry
    log.save(update_fields=[
        'response_status', 'response_body', 'attempts', 'last_attempted_at',
    ])
    logger.warning(
        'dispatch_webhook_task: non-2xx log=%s attempt=%d HTTP %s',
        log_id, log.attempts, resp.status_code,
    )
    return _retry_or_give_up(
        self, log, Exception(f'HTTP {resp.status_code}')
    )


def _retry_or_give_up(self, log, exc) -> dict:
    idx = self.request.retries
    countdown = _RETRY_DELAYS[idx] if idx < len(_RETRY_DELAYS) else _RETRY_DELAYS[-1]

    try:
        raise self.retry(exc=exc, countdown=countdown)
    except MaxRetriesExceededError:
        pass  # fall through to permanent-failure return below

    logger.error(
        'dispatch_webhook_task: permanently failed log=%s after %d attempts',
        log.pk, log.attempts,
    )
    return {'status': 'permanently_failed', 'attempts': log.attempts}

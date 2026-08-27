"""Periodic task: purge expired Idempotency-Key records."""
import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from services.idempotency_service import IDEMPOTENCY_TTL

logger = logging.getLogger(__name__)


@shared_task
def cleanup_expired_idempotency_keys() -> dict:
    """Delete IdempotencyKey rows older than the TTL — they can no longer be replayed."""
    from apps.accounts.models import IdempotencyKey

    cutoff = timezone.now() - IDEMPOTENCY_TTL - timedelta(hours=1)  # small grace margin
    deleted, _ = IdempotencyKey.objects.filter(created_at__lt=cutoff).delete()
    logger.info('cleanup_expired_idempotency_keys: deleted %d rows', deleted)
    return {'deleted': deleted}

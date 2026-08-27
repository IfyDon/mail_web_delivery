"""Periodic task: purge AuditLog rows past the 12-month retention window
promised on the dashboard's Audit Log page."""
import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

AUDIT_LOG_RETENTION = timedelta(days=365)


@shared_task
def cleanup_expired_audit_logs() -> dict:
    from apps.accounts.models import AuditLog

    cutoff = timezone.now() - AUDIT_LOG_RETENTION
    deleted, _ = AuditLog.objects.filter(created_at__lt=cutoff).delete()
    logger.info('cleanup_expired_audit_logs: deleted %d rows', deleted)
    return {'deleted': deleted}

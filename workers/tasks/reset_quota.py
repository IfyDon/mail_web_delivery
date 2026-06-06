"""Celery Beat task: reset monthly email quota counters for all users."""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def reset_monthly_quotas() -> dict:
    """Reset emails_sent_this_month to 0 for every Quota row.

    Designed to run on the 1st of each month via Celery Beat.
    Quota resets driven by Stripe invoice webhooks take precedence for
    paid subscribers; this task covers free-tier users and any edge cases.
    """
    from apps.accounts.models import Quota

    updated = Quota.objects.update(emails_sent_this_month=0)
    logger.info('reset_monthly_quotas: reset %d quota rows', updated)
    return {'quotas_reset': updated}

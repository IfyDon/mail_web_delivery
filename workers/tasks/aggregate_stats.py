"""Celery Beat task: rolls up Event rows into DailyStats for a given date."""
import logging
from datetime import date, timedelta

from celery import shared_task

from apps.analytics.aggregators import rollup_day

logger = logging.getLogger(__name__)


@shared_task
def aggregate_daily_stats(target_date_iso: str | None = None) -> dict:
    """Aggregate Event rows into DailyStats for *target_date_iso* (default: yesterday).

    Designed to run nightly via Celery Beat.  Safe to re-run — uses update_or_create.
    """
    target: date = (
        date.fromisoformat(target_date_iso)
        if target_date_iso
        else date.today() - timedelta(days=1)
    )

    users_processed = rollup_day(target)
    logger.info('aggregate_daily_stats: processed %d users for %s', users_processed, target)
    return {'date': target.isoformat(), 'users_processed': users_processed}

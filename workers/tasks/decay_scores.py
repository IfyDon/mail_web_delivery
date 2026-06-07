"""Celery task: apply monthly 10 % engagement score decay to all ContactEngagement rows."""

import logging

from celery import shared_task
from django.db import connection

logger = logging.getLogger(__name__)


@shared_task
def decay_engagement_scores() -> dict:
    """Multiply every ContactEngagement.score by 0.90 in a single UPDATE statement.

    Designed to run monthly via Celery Beat.
    Uses a raw SQL UPDATE for efficiency — avoids loading every row into Python.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE analytics_contactengagement SET score = ROUND(score * 0.90)"
        )
        rows = cursor.rowcount

    logger.info('decay_engagement_scores: decayed %d rows', rows)
    return {'rows_updated': rows}

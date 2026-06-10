"""
Celery task: rotate DKIM keys for verified sending domains every ROTATION_INTERVAL_DAYS days.

On rotation:
  - A new RSA-2048 key pair is generated.
  - The selector is updated to a date-based name (e.g. key20260610).
  - dkim_rotation_pending is set to True so the dashboard surfaces an alert.
  - dkim_verified is cleared so the domain re-enters verification after the user
    publishes the new DNS record.

The old key continues to sign mail already in flight until DNS propagates and the
domain passes re-verification.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.db import models as db_models
from django.utils import timezone

logger = logging.getLogger(__name__)

ROTATION_INTERVAL_DAYS = 90


@shared_task
def rotate_dkim_keys() -> dict:
    """Rotate DKIM keys for verified domains overdue for rotation."""
    from apps.domains.models import Domain

    cutoff = timezone.now() - timedelta(days=ROTATION_INTERVAL_DAYS)

    domains = Domain.objects.filter(
        verification_status='verified',
        dkim_rotation_pending=False,
    ).filter(
        db_models.Q(dkim_rotated_at__isnull=True)
        | db_models.Q(dkim_rotated_at__lt=cutoff)
    )

    rotated = 0
    for domain in domains.iterator():
        try:
            _rotate_domain(domain)
            rotated += 1
        except Exception:
            logger.exception('rotate_dkim_keys: failed for domain pk=%s', domain.pk)

    logger.info('rotate_dkim_keys: rotated %d domain(s)', rotated)
    return {'rotated': rotated}


def _rotate_domain(domain) -> None:
    now = timezone.now()
    new_selector = f"key{now.strftime('%Y%m%d')}"

    # Set all fields before calling generate_dkim_keys() because that method
    # calls domain.save() internally, which will persist everything at once.
    domain.dkim_selector = new_selector
    domain.dkim_rotation_pending = True
    domain.dkim_rotated_at = now
    domain.dkim_verified = False
    if domain.spf_verified and domain.dmarc_verified:
        domain.verification_status = 'pending'

    domain.generate_dkim_keys()  # generates keys, then calls self.save()

    logger.info(
        'rotate_dkim_keys: rotated domain=%s new_selector=%s',
        domain.domain, new_selector,
    )

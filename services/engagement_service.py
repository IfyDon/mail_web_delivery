"""Engagement scoring service.

Keeps ContactEngagement records up to date as events arrive.
Called from tracking views (open/click) and the SES inbound handler (bounce/complaint).
"""

import logging

from django.db import transaction

from apps.analytics.models import ContactEngagement

logger = logging.getLogger(__name__)


def update_score(user, email: str, event_type: str) -> ContactEngagement:
    """Atomically increment counters and adjust score for *email* owned by *user*.

    *event_type* must be one of: 'open', 'click', 'bounce', 'complaint'.
    Creates the row on first occurrence (upsert pattern).
    Returns the updated ContactEngagement instance.
    """
    email = email.lower().strip()

    with transaction.atomic():
        obj, _ = ContactEngagement.objects.select_for_update().get_or_create(
            user=user,
            email=email,
        )
        obj.apply_event(event_type)
        obj.save(update_fields=[
            'score', 'open_count', 'click_count',
            'bounce_count', 'complaint_count',
            'last_open', 'last_click', 'last_event', 'updated_at',
        ])

    logger.debug(
        'engagement: %s/%s event=%s new_score=%d',
        user.pk, email, event_type, obj.score,
    )
    return obj


def get_engagement(user, email: str) -> ContactEngagement | None:
    """Return the ContactEngagement record for *email*, or None if no history."""
    return ContactEngagement.objects.filter(
        user=user, email=email.lower().strip()
    ).first()


def top_contacts(user, limit: int = 20) -> list:
    """Return the top *limit* contacts by score (most engaged first)."""
    return list(
        ContactEngagement.objects.filter(user=user)
        .order_by('-score')[:limit]
    )


def bottom_contacts(user, limit: int = 20) -> list:
    """Return the bottom *limit* contacts by score (least engaged / at-risk first)."""
    return list(
        ContactEngagement.objects.filter(user=user)
        .order_by('score')[:limit]
    )

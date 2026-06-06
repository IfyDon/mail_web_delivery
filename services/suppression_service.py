"""Per-user suppression list: check before send, add on bounce/complaint/unsubscribe."""

from apps.suppressions.models import Suppression


def is_suppressed(user, email: str) -> bool:
    """Return True if *email* is on *user*'s suppression list."""
    return Suppression.objects.filter(
        user=user, email__iexact=email
    ).exists()


def add_suppression(user, email: str, reason: str) -> Suppression:
    """Add *email* to *user*'s suppression list (idempotent).

    *reason* must be one of Suppression.REASON_* constants.
    Returns the Suppression instance (created or existing).
    """
    obj, _ = Suppression.objects.get_or_create(
        user=user,
        email=email.lower().strip(),
        defaults={'reason': reason},
    )
    return obj

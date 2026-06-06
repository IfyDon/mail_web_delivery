"""Orchestrates send flow: suppression check → build headers → queue Celery task."""

from typing import Optional


def check_suppression(email: str, user=None) -> bool:
    """Return True if *email* is suppressed.

    If *user* is provided, checks the per-user Suppression table (preferred).
    Falls back to global Bounce/Complaint/Unsubscribe tables when user is None
    (used by legacy call sites or system tasks without user context).
    """
    if user is not None:
        from services.suppression_service import is_suppressed
        return is_suppressed(user, email)

    # Global fallback — used only when no user context is available
    from apps.suppressions.models import Bounce, Complaint, Unsubscribe
    if Unsubscribe.objects.filter(email__iexact=email).exists():
        return True
    if Bounce.objects.filter(email__iexact=email).exists():
        return True
    if Complaint.objects.filter(email__iexact=email).exists():
        return True
    return False


def make_list_unsubscribe_header(
    from_email: str, unsubscribe_url: Optional[str] = None
) -> str:
    """Return a List-Unsubscribe header value.

    Format: "<mailto:from_email>, <https://.../unsubscribe/<token>>"
    """
    parts = [f"<mailto:{from_email}>"]
    if unsubscribe_url:
        parts.append(f"<{unsubscribe_url}>")
    return ", ".join(parts)


def send_email(
    to_email: str,
    from_email: str,
    subject: str,
    html_body: str,
    text_body: str = "",
    unsubscribe_url: Optional[str] = None,
    user=None,
) -> dict:
    """Build headers/payload after suppression check.

    Raises ValueError if the recipient is suppressed.
    Returns {'headers': ..., 'payload': ...} for the transport layer.
    """
    if check_suppression(to_email, user=user):
        raise ValueError("Recipient is suppressed (unsubscribe/bounce/complaint)")

    headers = {
        "From": from_email,
        "To": to_email,
        "Subject": subject,
        "List-Unsubscribe": make_list_unsubscribe_header(from_email, unsubscribe_url),
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
    }
    payload = {"html": html_body, "text": text_body}
    return {"headers": headers, "payload": payload}


def queue_email(message_id: str) -> None:
    """Enqueue a saved Message record for async delivery via Celery."""
    from workers.tasks.send_email import send_email_task  # lazy — avoids circular import
    send_email_task.delay(str(message_id))

"""Lightweight tracking endpoints — no DRF overhead, plain Django views."""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.utils import timezone
from django.views import View

from services.tracking_service import TRANSPARENT_GIF
from tracking.tokens import verify_click_token, verify_open_token


def _client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


class OpenTrackingView(View):
    """Return a 1×1 transparent GIF and log an open event.

    Always returns the GIF — invalid tokens are silently ignored so
    email clients do not see a broken image.
    """

    def get(self, request, token):
        message_id = verify_open_token(token)
        if message_id:
            _record_open(request, message_id)
        return HttpResponse(TRANSPARENT_GIF, content_type="image/gif")


class ClickTrackingView(View):
    """Log a click event and 302-redirect to the original URL.

    Returns 400 only when the token is completely unreadable; legitimate
    old/expired tokens will still fail gracefully with a redirect to "/".
    """

    def get(self, request, token):
        data = verify_click_token(token)
        if data is None:
            return HttpResponseBadRequest("Invalid tracking token.")

        message_id = data.get("message_id", "")
        url = data.get("url", "")

        if message_id and url:
            _record_click(request, message_id, url)

        return HttpResponseRedirect(url or "/")


# ── Event helpers (lazy DB imports to keep module load fast) ──────────────────

def _record_open(request, message_id: str) -> None:
    from apps.email_messages.models import Message
    from apps.events.models import Event

    try:
        msg = Message.objects.get(pk=message_id)
    except (Message.DoesNotExist, ValidationError):
        return

    # De-duplicate: at most one open event per message per 24-hour window
    cutoff = timezone.now() - timedelta(hours=24)
    if Event.objects.filter(
        message=msg, type=Event.TYPE_OPEN, timestamp__gte=cutoff
    ).exists():
        return

    Event.objects.create(
        message=msg,
        type=Event.TYPE_OPEN,
        metadata={
            "ip": _client_ip(request),
            "user_agent": request.META.get("HTTP_USER_AGENT", ""),
        },
    )


def _record_click(request, message_id: str, url: str) -> None:
    from apps.email_messages.models import Message
    from apps.events.models import Event

    try:
        msg = Message.objects.get(pk=message_id)
    except (Message.DoesNotExist, ValidationError):
        return

    Event.objects.create(
        message=msg,
        type=Event.TYPE_CLICK,
        metadata={
            "url": url,
            "ip": _client_ip(request),
            "user_agent": request.META.get("HTTP_USER_AGENT", ""),
        },
    )

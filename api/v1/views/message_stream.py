"""GET /api/v1/messages/stream/ — Server-Sent Events for real-time message status updates.

The client opens a long-lived connection; the server pushes a JSON event
whenever a message belonging to the authenticated user changes status.

Implementation: poll-based SSE (no external pub/sub required).
The endpoint queries for messages updated in the last poll window and yields
one `data:` line per changed message, then waits POLL_INTERVAL seconds.

The client (EventSource) automatically reconnects on disconnect.
"""
import json
import time
import logging

from django.http import StreamingHttpResponse
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated

from apps.email_messages.models import Message

logger = logging.getLogger(__name__)

POLL_INTERVAL = 5   # seconds between DB polls
MAX_LIFETIME  = 300 # close after 5 minutes; client reconnects automatically
HEARTBEAT_EVERY = 15  # send a comment keepalive this often


def message_stream_view(request):
    """Authenticate then stream SSE events for the authenticated user."""
    # DRF auth classes don't hook into plain Django views, so we authenticate
    # manually using the same classes registered in settings.
    user = _authenticate(request)
    if user is None:
        return StreamingHttpResponse(
            _error_event("Authentication credentials were not provided."),
            content_type="text/event-stream",
            status=401,
        )

    response = StreamingHttpResponse(
        _event_generator(user),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"  # disable nginx buffering
    return response


# ── Authentication ────────────────────────────────────────────────────────────

def _authenticate(request):
    """Return the authenticated user or None."""
    for AuthClass in (TokenAuthentication, SessionAuthentication):
        try:
            result = AuthClass().authenticate(request)
            if result is not None:
                return result[0]
        except (AuthenticationFailed, NotAuthenticated):
            pass
    return None


# ── Generator ─────────────────────────────────────────────────────────────────

def _event_generator(user):
    """Yield SSE-formatted bytes for message status changes."""
    from django.utils import timezone
    from datetime import timedelta

    deadline = time.monotonic() + MAX_LIFETIME
    last_heartbeat = time.monotonic()
    # Track the last time we polled so we only emit genuinely new changes
    cursor = timezone.now() - timedelta(seconds=POLL_INTERVAL)

    yield b": connected\n\n"

    while time.monotonic() < deadline:
        now = timezone.now()
        try:
            changed = list(
                Message.objects
                .filter(user=user, updated_at__gte=cursor)
                .values("id", "status", "recipient_email", "subject", "updated_at")
                .order_by("updated_at")[:50]
            )
        except Exception:
            logger.exception("message_stream: DB poll error")
            changed = []

        cursor = now

        for msg in changed:
            payload = {
                "id":              str(msg["id"]),
                "status":          msg["status"],
                "recipient_email": msg["recipient_email"],
                "subject":         msg["subject"],
                "updated_at":      msg["updated_at"].isoformat(),
            }
            line = f"data: {json.dumps(payload)}\n\n"
            yield line.encode()

        # Heartbeat comment to keep the connection alive through proxies
        if time.monotonic() - last_heartbeat >= HEARTBEAT_EVERY:
            yield b": heartbeat\n\n"
            last_heartbeat = time.monotonic()

        time.sleep(POLL_INTERVAL)

    # Graceful close — client's EventSource will reconnect
    yield b"event: close\ndata: {}\n\n"


def _error_event(message):
    yield f"event: error\ndata: {json.dumps({'detail': message})}\n\n".encode()

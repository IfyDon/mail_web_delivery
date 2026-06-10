"""Injects a UUID X-Request-ID header into every request and response.

The ID is:
- Read from the incoming `X-Request-ID` header if the upstream proxy/load
  balancer already sets one (trust but validate — must be a valid UUID4).
- Otherwise generated fresh for every request.

The value is stored on `request.request_id` so views and structured log
formatters can include it without another header lookup.
"""
import logging
import uuid

logger = logging.getLogger(__name__)

_HEADER = "X-Request-ID"
_META   = "HTTP_X_REQUEST_ID"


class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = _parse_or_generate(
            request.META.get(_META, "")
        )

        response = self.get_response(request)
        response[_HEADER] = request.request_id
        return response


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_or_generate(raw: str) -> str:
    """Return *raw* if it is a valid UUID4 string, otherwise generate a new one."""
    if raw:
        try:
            uid = uuid.UUID(raw, version=4)
            return str(uid)
        except ValueError:
            pass
    return str(uuid.uuid4())

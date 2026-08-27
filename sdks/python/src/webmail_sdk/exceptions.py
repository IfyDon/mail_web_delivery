"""Exception hierarchy for the WebMail SDK.

Every error the API can return maps to one of these, so callers can catch
broadly (WebMailError) or narrowly (RateLimitError) as needed.
"""
from __future__ import annotations

from typing import Any


class WebMailError(Exception):
    """Base class for every exception this SDK raises."""

    def __init__(self, message: str, *, status_code: int | None = None, body: Any = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.body = body

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.message!r}, status_code={self.status_code!r})"


class AuthenticationError(WebMailError):
    """401 — the API key is missing or invalid."""


class ForbiddenError(WebMailError):
    """403 — authenticated, but not allowed to do this."""


class NotFoundError(WebMailError):
    """404 — the resource doesn't exist (or isn't yours)."""


class ValidationError(WebMailError):
    """400/422 — the request was rejected. `.body` usually has field-level detail."""


class PaymentRequiredError(WebMailError):
    """402 — monthly email quota exceeded."""


class ConflictError(WebMailError):
    """409 — an Idempotency-Key was reused with a different request body."""


class RateLimitError(WebMailError):
    """429 — too many requests. `.retry_after` is seconds to wait, if known."""

    def __init__(self, message: str, *, status_code=None, body=None, retry_after: float | None = None):
        super().__init__(message, status_code=status_code, body=body)
        self.retry_after = retry_after


class APIError(WebMailError):
    """Anything else — including 5xx server errors."""


def raise_for_status(status_code: int, body: Any, *, retry_after: float | None = None) -> None:
    """Translate an HTTP status code into the matching WebMailError subclass."""
    message = _extract_message(body) or f"Request failed with status {status_code}"

    if status_code == 401:
        raise AuthenticationError(message, status_code=status_code, body=body)
    if status_code == 402:
        raise PaymentRequiredError(message, status_code=status_code, body=body)
    if status_code == 403:
        raise ForbiddenError(message, status_code=status_code, body=body)
    if status_code == 404:
        raise NotFoundError(message, status_code=status_code, body=body)
    if status_code == 409:
        raise ConflictError(message, status_code=status_code, body=body)
    if status_code == 429:
        raise RateLimitError(message, status_code=status_code, body=body, retry_after=retry_after)
    if status_code in (400, 422):
        raise ValidationError(message, status_code=status_code, body=body)
    raise APIError(message, status_code=status_code, body=body)


def _extract_message(body: Any) -> str | None:
    if isinstance(body, dict):
        if isinstance(body.get("message"), str):
            return body["message"]
        errors = body.get("errors")
        if isinstance(errors, list) and errors:
            first = errors[0]
            if isinstance(first, dict):
                field = first.get("field", "")
                msg = first.get("message", "")
                return f"{field}: {msg}" if field else msg
        if isinstance(body.get("detail"), str):
            return body["detail"]
    return None

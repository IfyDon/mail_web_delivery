"""Idempotency-Key support for the send API.

Clients that retry a request (network blip, timeout, at-least-once queue)
attach the same `Idempotency-Key` header. Replaying that header within the
TTL window returns the original response instead of sending a duplicate
email. Reusing a key with a *different* request body is treated as a
client error, matching the convention Stripe/Resend use.
"""
import hashlib
import json
from datetime import timedelta

from django.utils import timezone

IDEMPOTENCY_TTL = timedelta(hours=24)


def hash_request_body(data) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, default=str).encode()
    ).hexdigest()


def get_idempotency_key(request) -> str:
    return request.META.get('HTTP_IDEMPOTENCY_KEY', '').strip()


def check_idempotency(user, endpoint: str, key: str, request_hash: str):
    """Return (cached_response_or_None, conflict_bool).

    cached_response is a dict {'status': int, 'body': ...} to replay verbatim
    if this exact (key, request body) was already handled and hasn't expired.
    conflict_bool is True if the key was reused with a *different* body.
    """
    from apps.accounts.models import IdempotencyKey

    existing = IdempotencyKey.objects.filter(user=user, endpoint=endpoint, key=key).first()
    if existing is None:
        return None, False

    if timezone.now() - existing.created_at > IDEMPOTENCY_TTL:
        existing.delete()
        return None, False

    if existing.request_hash != request_hash:
        return None, True

    return {'status': existing.response_status, 'body': existing.response_body}, False


def store_idempotency(user, endpoint: str, key: str, request_hash: str, status_code: int, body: dict) -> None:
    from django.db import IntegrityError

    from apps.accounts.models import IdempotencyKey

    try:
        IdempotencyKey.objects.create(
            user=user, endpoint=endpoint, key=key,
            request_hash=request_hash, response_status=status_code, response_body=body,
        )
    except IntegrityError:
        # Lost a race with a concurrent identical request — the other one's
        # stored result is authoritative; nothing to do here.
        pass

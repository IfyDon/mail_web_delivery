"""HMAC-signed open tokens and Fernet-encrypted click tokens.

Open token:  base64url(message_id) + "." + HMAC-SHA256 signature
             Stateless, no TTL — we de-dup opens at the view layer.

Click token: Fernet(json({message_id, url}))
             Tamper-proof and hides the original URL from the token string.
"""

import base64
import hashlib
import hmac
import json

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _fernet() -> Fernet:
    """Derive a stable Fernet key from Django's SECRET_KEY."""
    raw = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(raw))


# ── Open tracking (HMAC) ──────────────────────────────────────────────────────

def generate_open_token(message_id: str) -> str:
    """Return a URL-safe HMAC-signed token for open tracking."""
    data = message_id.encode()
    sig = hmac.new(settings.SECRET_KEY.encode(), data, hashlib.sha256).hexdigest()
    encoded = base64.urlsafe_b64encode(data).decode().rstrip("=")
    return f"{encoded}.{sig}"


def verify_open_token(token: str) -> str | None:
    """Return message_id if the token signature is valid, else None."""
    try:
        encoded, sig = token.split(".", 1)
        padding = "=" * (-len(encoded) % 4)
        data = base64.urlsafe_b64decode(encoded + padding)
        expected = hmac.new(settings.SECRET_KEY.encode(), data, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        return data.decode()
    except Exception:  # noqa: BLE001
        return None


# ── Click tracking (Fernet) ───────────────────────────────────────────────────

def generate_click_token(message_id: str, url: str) -> str:
    """Return a URL-safe Fernet-encrypted token carrying message_id + original URL."""
    payload = json.dumps({"message_id": message_id, "url": url}).encode()
    return _fernet().encrypt(payload).decode()


def verify_click_token(token: str) -> dict | None:
    """Return {'message_id': ..., 'url': ...} if valid, else None."""
    try:
        payload = _fernet().decrypt(token.encode())
        return json.loads(payload)
    except (InvalidToken, Exception):  # noqa: BLE001
        return None


# ── Unsubscribe tracking (HMAC, 30-day TTL) ──────────────────────────────────

def generate_unsubscribe_token(user_id: str, email: str) -> str:
    """Return a URL-safe HMAC-signed token encoding user_id + email + expiry.

    Token format: base64url("{user_id}:{email}:{expires}") + "." + HMAC
    """
    import time
    expires = int(time.time()) + (30 * 24 * 3600)  # 30-day TTL
    payload = f"{user_id}:{email.lower().strip()}:{expires}"
    sig = hmac.new(settings.SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    encoded = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    return f"{encoded}.{sig}"


def verify_unsubscribe_token(token: str) -> dict | None:
    """Return {'user_id': ..., 'email': ...} if the token is valid and unexpired, else None."""
    import time
    try:
        encoded, sig = token.split(".", 1)
        padding = "=" * (-len(encoded) % 4)
        payload = base64.urlsafe_b64decode(encoded + padding).decode()
        expected = hmac.new(settings.SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        user_id, email, expires_str = payload.split(":", 2)
        if int(time.time()) > int(expires_str):
            return None
        return {"user_id": user_id, "email": email}
    except Exception:  # noqa: BLE001
        return None

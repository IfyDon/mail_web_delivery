"""Unit tests for tracking tokens and crypto utilities."""
import pytest
from unittest.mock import patch


class TestOpenTrackingTokens:
    def test_generate_and_verify_roundtrip(self, settings):
        settings.SECRET_KEY = "test-secret-key-for-tokens"
        from tracking.tokens import generate_open_token, verify_open_token
        msg_id = "550e8400-e29b-41d4-a716-446655440000"
        token = generate_open_token(msg_id)
        assert verify_open_token(token) == msg_id

    def test_tampered_token_rejected(self, settings):
        settings.SECRET_KEY = "test-secret-key-for-tokens"
        from tracking.tokens import generate_open_token, verify_open_token
        token = generate_open_token("msg-123")
        tampered = token[:-4] + "xxxx"
        assert verify_open_token(tampered) is None

    def test_garbage_token_returns_none(self, settings):
        settings.SECRET_KEY = "test-secret-key-for-tokens"
        from tracking.tokens import verify_open_token
        assert verify_open_token("not.a.valid.token.at.all") is None

    def test_token_is_url_safe(self, settings):
        settings.SECRET_KEY = "test-secret-key-for-tokens"
        from tracking.tokens import generate_open_token
        token = generate_open_token("some-message-id")
        assert " " not in token
        assert "+" not in token
        assert "/" not in token


class TestClickTrackingTokens:
    def test_generate_and_verify_roundtrip(self, settings):
        settings.SECRET_KEY = "test-secret-key-for-tokens"
        from tracking.tokens import generate_click_token, verify_click_token
        msg_id = "msg-abc-123"
        url = "https://example.com/landing?ref=email"
        token = generate_click_token(msg_id, url)
        result = verify_click_token(token)
        assert result is not None
        assert result["message_id"] == msg_id
        assert result["url"] == url

    def test_tampered_token_rejected(self, settings):
        settings.SECRET_KEY = "test-secret-key-for-tokens"
        from tracking.tokens import generate_click_token, verify_click_token
        token = generate_click_token("msg-1", "https://example.com")
        assert verify_click_token("AAAA" + token[4:]) is None

    def test_garbage_returns_none(self, settings):
        settings.SECRET_KEY = "test-secret-key-for-tokens"
        from tracking.tokens import verify_click_token
        assert verify_click_token("completelygarbagetoken") is None

    def test_url_preserved_exactly(self, settings):
        settings.SECRET_KEY = "test-secret-key-for-tokens"
        from tracking.tokens import generate_click_token, verify_click_token
        url = "https://example.com/path?a=1&b=2#anchor"
        token = generate_click_token("m", url)
        assert verify_click_token(token)["url"] == url


class TestUnsubscribeTokens:
    def test_generate_and_verify_roundtrip(self, settings):
        settings.SECRET_KEY = "test-secret-key-for-tokens"
        from tracking.tokens import generate_unsubscribe_token, verify_unsubscribe_token
        token = generate_unsubscribe_token("42", "user@example.com")
        result = verify_unsubscribe_token(token)
        assert result is not None
        assert result["user_id"] == "42"
        assert result["email"] == "user@example.com"

    def test_expired_token_rejected(self, settings):
        settings.SECRET_KEY = "test-secret-key-for-tokens"
        from tracking.tokens import verify_unsubscribe_token
        import base64, hashlib, hmac, time
        expires = int(time.time()) - 1  # already expired
        payload = f"1:user@example.com:{expires}"
        sig = hmac.new(
            settings.SECRET_KEY.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        encoded = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
        token = f"{encoded}.{sig}"
        assert verify_unsubscribe_token(token) is None

    def test_tampered_token_rejected(self, settings):
        settings.SECRET_KEY = "test-secret-key-for-tokens"
        from tracking.tokens import generate_unsubscribe_token, verify_unsubscribe_token
        token = generate_unsubscribe_token("1", "user@example.com")
        tampered = token[:-4] + "xxxx"
        assert verify_unsubscribe_token(tampered) is None

    def test_email_normalised(self, settings):
        settings.SECRET_KEY = "test-secret-key-for-tokens"
        from tracking.tokens import generate_unsubscribe_token, verify_unsubscribe_token
        token = generate_unsubscribe_token("1", "  User@Example.COM  ")
        result = verify_unsubscribe_token(token)
        assert result["email"] == "user@example.com"

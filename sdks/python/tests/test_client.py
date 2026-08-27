import pytest
import responses

from webmail_sdk import AuthenticationError, RateLimitError, ValidationError


BASE = "https://webmailapi.test"


class TestAuth:
    def test_missing_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("WEBMAIL_API_KEY", raising=False)
        from webmail_sdk import WebMail
        with pytest.raises(ValueError):
            WebMail(api_key=None)

    def test_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("WEBMAIL_API_KEY", "sk_env_123")
        from webmail_sdk import WebMail
        c = WebMail()
        assert c.api_key == "sk_env_123"

    @responses.activate
    def test_sends_bearer_header(self, client):
        responses.add(
            responses.GET, f"{BASE}/api/v1/domains/",
            json={"count": 0, "next": None, "previous": None, "results": []}, status=200,
        )
        client.domains.list()
        assert responses.calls[0].request.headers["Authorization"] == "Bearer sk_test_123"


class TestErrorMapping:
    @responses.activate
    def test_401_raises_authentication_error(self, client):
        responses.add(
            responses.GET, f"{BASE}/api/v1/domains/",
            json={"detail": "Invalid token."}, status=401,
        )
        with pytest.raises(AuthenticationError) as exc_info:
            client.domains.list()
        assert exc_info.value.status_code == 401
        assert exc_info.value.message == "Invalid token."

    @responses.activate
    def test_422_raises_validation_error(self, client):
        responses.add(
            responses.POST, f"{BASE}/api/v1/send",
            json={"status": "error", "code": 422, "errors": [
                {"field": "from_address", "message": "Sender domain is not verified."}
            ]},
            status=422,
        )
        with pytest.raises(ValidationError) as exc_info:
            client.emails.send(
                to="a@example.com", from_address="noreply@unverified.com",
                subject="Hi", html_body="<p>hi</p>",
            )
        assert "from_address" in exc_info.value.message

    @responses.activate
    def test_429_carries_retry_after(self, client):
        responses.add(
            responses.GET, f"{BASE}/api/v1/domains/",
            json={"message": "Too many requests."}, status=429,
            headers={"Retry-After": "12"},
        )
        with pytest.raises(RateLimitError) as exc_info:
            client.domains.list()
        assert exc_info.value.retry_after == 12.0

    @responses.activate
    def test_204_no_content_returns_none(self, client):
        responses.add(responses.DELETE, f"{BASE}/api/v1/domains/1/", status=204)
        result = client.domains.delete(1)
        assert result is None

"""Optional smoke test against the real production API.

Skipped unless WEBMAIL_LIVE_TEST_KEY is set — never runs in normal CI/dev.
Only exercises safe, read-only (and self-cleaning) operations.
"""
import os
import uuid

import pytest

from webmail_sdk import WebMail

LIVE_KEY = os.environ.get("WEBMAIL_LIVE_TEST_KEY")

pytestmark = pytest.mark.skipif(not LIVE_KEY, reason="WEBMAIL_LIVE_TEST_KEY not set")


@pytest.fixture
def live_client():
    return WebMail(api_key=LIVE_KEY, base_url="https://webmailapi.com")


def test_list_domains(live_client):
    domains = live_client.domains.list()
    assert isinstance(domains, list)


def test_list_messages(live_client):
    messages = live_client.messages.list()
    assert isinstance(messages, list)


def test_get_stats(live_client):
    stats = live_client.stats.get(date_range="7d")
    assert "totals" in stats
    assert "daily" in stats


def test_list_webhooks(live_client):
    webhooks = live_client.webhooks.list()
    assert isinstance(webhooks, list)


def test_list_templates(live_client):
    templates = live_client.templates.list()
    assert isinstance(templates, list)


def test_list_suppressions(live_client):
    result = live_client.suppressions.list()
    assert "suppressions" in result


def test_list_streams(live_client):
    streams = live_client.streams.list()
    assert isinstance(streams, list)


def test_stream_create_get_delete_roundtrip(live_client):
    slug = f"sdk-smoke-{uuid.uuid4().hex[:8]}"
    created = live_client.streams.create(name="SDK Smoke Test", slug=slug)
    assert created["slug"] == slug

    fetched = live_client.streams.get(slug)
    assert fetched["slug"] == slug

    live_client.streams.delete(slug)


def test_invalid_api_key_raises_authentication_error():
    from webmail_sdk import AuthenticationError

    bad_client = WebMail(api_key="sk_live_totally_invalid_key", base_url="https://webmailapi.com")
    with pytest.raises(AuthenticationError):
        bad_client.domains.list()


def test_send_without_verified_domain_raises_validation_error(live_client):
    from webmail_sdk import ValidationError

    with pytest.raises(ValidationError):
        live_client.emails.send(
            to="sdk-smoke-test@example.com",
            from_address=f"noreply@{uuid.uuid4().hex[:8]}-unverified-sdk-test.com",
            subject="SDK smoke test",
            html_body="<p>should be rejected — unverified domain</p>",
        )

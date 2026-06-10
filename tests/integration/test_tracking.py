"""Integration tests for open/click tracking views."""
import pytest
from django.test import Client
from unittest.mock import patch


@pytest.mark.django_db
class TestOpenTrackingView:
    def test_returns_gif(self, settings, sent_message):
        settings.SECRET_KEY = "test-secret-key"
        from tracking.tokens import generate_open_token
        token = generate_open_token(str(sent_message.pk))
        client = Client()
        resp = client.get(f"/tracking/open/{token}/")
        assert resp.status_code == 200
        assert resp["Content-Type"] == "image/gif"

    def test_invalid_token_still_returns_gif(self, settings):
        settings.SECRET_KEY = "test-secret-key"
        client = Client()
        resp = client.get("/tracking/open/invalidtoken.badsig/")
        assert resp.status_code == 200
        assert resp["Content-Type"] == "image/gif"

    def test_creates_open_event(self, settings, sent_message):
        settings.SECRET_KEY = "test-secret-key"
        from apps.events.models import Event
        from tracking.tokens import generate_open_token
        token = generate_open_token(str(sent_message.pk))
        client = Client()
        client.get(f"/tracking/open/{token}/")
        assert Event.objects.filter(
            message=sent_message, type=Event.TYPE_OPEN
        ).exists()

    def test_deduplicates_opens_within_24h(self, settings, sent_message):
        settings.SECRET_KEY = "test-secret-key"
        from apps.events.models import Event
        from tracking.tokens import generate_open_token
        token = generate_open_token(str(sent_message.pk))
        client = Client()
        client.get(f"/tracking/open/{token}/")
        client.get(f"/tracking/open/{token}/")
        assert Event.objects.filter(
            message=sent_message, type=Event.TYPE_OPEN
        ).count() == 1

    def test_open_event_includes_metadata(self, settings, sent_message):
        settings.SECRET_KEY = "test-secret-key"
        from apps.events.models import Event
        from tracking.tokens import generate_open_token
        token = generate_open_token(str(sent_message.pk))
        client = Client()
        client.get(
            f"/tracking/open/{token}/",
            HTTP_USER_AGENT="Mozilla/5.0",
        )
        event = Event.objects.filter(message=sent_message, type=Event.TYPE_OPEN).first()
        assert event is not None
        assert "user_agent" in event.metadata


@pytest.mark.django_db
class TestClickTrackingView:
    def test_redirects_to_url(self, settings, sent_message):
        settings.SECRET_KEY = "test-secret-key"
        from tracking.tokens import generate_click_token
        target_url = "https://example.com/landing"
        token = generate_click_token(str(sent_message.pk), target_url)
        client = Client()
        resp = client.get(f"/tracking/click/{token}/")
        assert resp.status_code == 302
        assert resp["Location"] == target_url

    def test_invalid_token_returns_400(self, settings):
        settings.SECRET_KEY = "test-secret-key"
        client = Client()
        resp = client.get("/tracking/click/completelygarbagetoken/")
        assert resp.status_code == 400

    def test_creates_click_event(self, settings, sent_message):
        settings.SECRET_KEY = "test-secret-key"
        from apps.events.models import Event
        from tracking.tokens import generate_click_token
        token = generate_click_token(str(sent_message.pk), "https://example.com")
        client = Client()
        client.get(f"/tracking/click/{token}/")
        assert Event.objects.filter(
            message=sent_message, type=Event.TYPE_CLICK
        ).exists()

    def test_click_event_records_url(self, settings, sent_message):
        settings.SECRET_KEY = "test-secret-key"
        from apps.events.models import Event
        from tracking.tokens import generate_click_token
        url = "https://example.com/promo"
        token = generate_click_token(str(sent_message.pk), url)
        client = Client()
        client.get(f"/tracking/click/{token}/")
        event = Event.objects.filter(message=sent_message, type=Event.TYPE_CLICK).first()
        assert event.metadata["url"] == url

    def test_multiple_clicks_all_recorded(self, settings, sent_message):
        settings.SECRET_KEY = "test-secret-key"
        from apps.events.models import Event
        from tracking.tokens import generate_click_token
        token = generate_click_token(str(sent_message.pk), "https://example.com")
        client = Client()
        client.get(f"/tracking/click/{token}/")
        client.get(f"/tracking/click/{token}/")
        assert Event.objects.filter(
            message=sent_message, type=Event.TYPE_CLICK
        ).count() == 2

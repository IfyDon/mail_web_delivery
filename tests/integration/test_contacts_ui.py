"""Integration tests for the Contacts (engagement scoring) dashboard page."""
import pytest
from django.test import Client

from apps.analytics.models import ContactEngagement


@pytest.fixture
def dashboard_client(user):
    client = Client()
    client.force_login(user)
    return client


def _make(user, email, **kwargs):
    return ContactEngagement.objects.create(user=user, email=email, **kwargs)


@pytest.mark.django_db
class TestContactsView:
    def test_renders_empty_state(self, dashboard_client):
        resp = dashboard_client.get("/dashboard/contacts/")
        assert resp.status_code == 200
        assert resp.context["total_tracked"] == 0

    def test_lists_only_own_contacts(self, dashboard_client, user, second_user):
        _make(user, "mine@example.com", score=5)
        _make(second_user, "not-mine@example.com", score=5)
        resp = dashboard_client.get("/dashboard/contacts/")
        emails = {c.email for c in resp.context["contacts"]}
        assert emails == {"mine@example.com"}

    def test_default_sort_is_score_desc(self, dashboard_client, user):
        _make(user, "low@example.com", score=1)
        _make(user, "high@example.com", score=10)
        resp = dashboard_client.get("/dashboard/contacts/")
        emails = [c.email for c in resp.context["contacts"]]
        assert emails == ["high@example.com", "low@example.com"]

    def test_engaged_segment_excludes_zero_and_negative(self, dashboard_client, user):
        _make(user, "positive@example.com", score=5)
        _make(user, "zero@example.com", score=0)
        _make(user, "negative@example.com", score=-5)
        resp = dashboard_client.get("/dashboard/contacts/?segment=engaged")
        emails = {c.email for c in resp.context["contacts"]}
        assert emails == {"positive@example.com"}

    def test_at_risk_segment_sorts_ascending(self, dashboard_client, user):
        _make(user, "very-bad@example.com", score=-50)
        _make(user, "bit-bad@example.com", score=-5)
        _make(user, "positive@example.com", score=5)
        resp = dashboard_client.get("/dashboard/contacts/?segment=at_risk")
        emails = [c.email for c in resp.context["contacts"]]
        assert emails == ["very-bad@example.com", "bit-bad@example.com"]

    def test_search_filters_by_email_substring(self, dashboard_client, user):
        _make(user, "alice@example.com", score=1)
        _make(user, "bob@example.com", score=1)
        resp = dashboard_client.get("/dashboard/contacts/?q=alice")
        emails = {c.email for c in resp.context["contacts"]}
        assert emails == {"alice@example.com"}

    def test_summary_counts(self, dashboard_client, user):
        _make(user, "a@example.com", score=10)
        _make(user, "b@example.com", score=-10)
        _make(user, "c@example.com", score=0)
        resp = dashboard_client.get("/dashboard/contacts/")
        assert resp.context["total_tracked"] == 3
        assert resp.context["engaged_count"] == 1
        assert resp.context["at_risk_count"] == 1
        assert resp.context["avg_score"] == 0

    def test_requires_login(self):
        resp = Client().get("/dashboard/contacts/")
        assert resp.status_code == 302
        assert "/login/" in resp.get("Location", "")

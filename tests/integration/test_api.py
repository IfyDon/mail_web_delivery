"""Integration tests for REST API endpoints."""
import pytest
from django.urls import reverse


# ── Auth endpoints ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAuthRegister:
    url = "/api/v1/auth/register/"

    def test_register_success(self, api_client):
        resp = api_client.post(self.url, {
            "email": "newuser@example.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        })
        assert resp.status_code == 201
        assert "token" in resp.data

    def test_register_duplicate_email(self, api_client, user):
        resp = api_client.post(self.url, {
            "email": user.email,
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        })
        assert resp.status_code == 400

    def test_register_missing_fields(self, api_client):
        resp = api_client.post(self.url, {"email": "x@x.com"})
        assert resp.status_code == 400


@pytest.mark.django_db
class TestAuthLogin:
    url = "/api/v1/auth/login/"

    def test_login_success(self, api_client, user):
        resp = api_client.post(self.url, {
            "email": user.email,
            "password": "testpass123",
        })
        assert resp.status_code == 200
        assert "token" in resp.data

    def test_login_wrong_password(self, api_client, user):
        resp = api_client.post(self.url, {
            "email": user.email,
            "password": "wrongpass",
        })
        assert resp.status_code == 400

    def test_login_unknown_email(self, api_client):
        resp = api_client.post(self.url, {
            "email": "nobody@example.com",
            "password": "irrelevant",
        })
        assert resp.status_code == 400


@pytest.mark.django_db
class TestAuthMe:
    url = "/api/v1/auth/me/"

    def test_me_requires_auth(self, api_client):
        resp = api_client.get(self.url)
        assert resp.status_code == 401

    def test_me_returns_user(self, authed_client, user):
        resp = authed_client.get(self.url)
        assert resp.status_code == 200
        assert resp.data["email"] == user.email

    def test_me_patch_updates_name(self, authed_client, user):
        resp = authed_client.patch(self.url, {"first_name": "Alice"})
        assert resp.status_code == 200
        user.refresh_from_db()
        assert user.first_name == "Alice"


# ── Send endpoint ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSendView:
    url = "/api/v1/send"

    def _payload(self, **overrides):
        data = {
            "to": "recipient@example.com",
            "from": "sender@example.com",
            "subject": "Test",
            "html_body": "<p>Hi</p>",
        }
        data.update(overrides)
        return data

    def test_send_requires_auth(self, api_client):
        resp = api_client.post(self.url, self._payload())
        assert resp.status_code == 401

    def test_send_unverified_domain_returns_422(self, authed_client, quota):
        resp = authed_client.post(self.url, self._payload(), format="json")
        assert resp.status_code == 422

    def test_send_queues_message(self, authed_client, domain, quota):
        from apps.email_messages.models import Message
        resp = authed_client.post(self.url, self._payload(
            **{"from": f"sender@{domain.domain}"}
        ), format="json")
        assert resp.status_code == 202
        assert resp.data["status"] in ("queued", "scheduled")
        assert Message.objects.filter(user__email="test@example.com").exists()

    def test_send_suppressed_recipient_accepted(self, authed_client, domain, quota, suppression):
        resp = authed_client.post(self.url, self._payload(
            to=suppression.email,
            **{"from": f"sender@{domain.domain}"}
        ), format="json")
        assert resp.status_code == 202
        assert resp.data["status"] == "suppressed"

    def test_send_quota_exceeded_returns_402(self, authed_client, domain, quota):
        quota.emails_sent_this_month = quota.monthly_limit
        quota.save()
        resp = authed_client.post(self.url, self._payload(
            **{"from": f"sender@{domain.domain}"}
        ), format="json")
        assert resp.status_code == 402

    def test_send_scheduled_with_send_at(self, authed_client, domain, quota):
        from apps.email_messages.models import Message
        resp = authed_client.post(self.url, self._payload(
            **{"from": f"sender@{domain.domain}", "send_at": "2035-01-01T10:00:00Z"}
        ), format="json")
        assert resp.status_code == 202
        assert resp.data["status"] == "scheduled"
        msg = Message.objects.get(id=resp.data["message_id"])
        assert msg.scheduled_at is not None


@pytest.mark.django_db
class TestBatchSendView:
    url = "/api/v1/send/batch"

    def test_empty_list_returns_400(self, authed_client):
        resp = authed_client.post(self.url, {"messages": []}, format="json")
        assert resp.status_code == 400

    def test_over_500_returns_400(self, authed_client):
        messages = [
            {"to": "r@example.com", "from": "s@example.com",
             "subject": "S", "html_body": "<p>H</p>"}
        ] * 501
        resp = authed_client.post(self.url, {"messages": messages}, format="json")
        assert resp.status_code == 400

    def test_batch_send_success(self, authed_client, domain, quota):
        messages = [
            {"to": "r@example.com", "from": f"s@{domain.domain}",
             "subject": "S", "html_body": "<p>H</p>"}
        ]
        resp = authed_client.post(self.url, {"messages": messages}, format="json")
        assert resp.status_code == 202
        assert resp.data["results"][0]["status"] == "queued"


# ── Messages list / detail ────────────────────────────────────────────────────

@pytest.mark.django_db
class TestMessageListView:
    url = "/api/v1/messages/"

    def test_requires_auth(self, api_client):
        assert api_client.get(self.url).status_code == 401

    def test_lists_own_messages(self, authed_client, message):
        resp = authed_client.get(self.url)
        assert resp.status_code == 200
        assert resp.data["count"] >= 1

    def test_filters_by_status(self, authed_client, message, sent_message):
        resp = authed_client.get(self.url + "?status=sent")
        assert resp.status_code == 200
        for item in resp.data["results"]:
            assert item["status"] == "sent"

    def test_other_users_messages_not_visible(self, authed_client, second_user, domain):
        from apps.email_messages.models import Message
        Message.objects.create(
            user=second_user, domain=domain,
            to_address="r@r.com", from_address="s@s.com",
            subject="Other", html_body="<p>X</p>",
        )
        resp = authed_client.get(self.url)
        for item in resp.data["results"]:
            assert item["from_address"] != "s@s.com"


@pytest.mark.django_db
class TestMessageDetailView:
    def test_returns_detail_with_events(self, authed_client, sent_message, open_event):
        resp = authed_client.get(f"/api/v1/messages/{sent_message.id}/")
        assert resp.status_code == 200
        assert len(resp.data["events"]) == 1
        assert resp.data["events"][0]["type"] == "open"

    def test_404_for_other_users_message(self, authed_client, second_user, domain):
        from apps.email_messages.models import Message
        msg = Message.objects.create(
            user=second_user, domain=domain,
            to_address="r@r.com", from_address="s@s.com",
            subject="X", html_body="<p>X</p>",
        )
        resp = authed_client.get(f"/api/v1/messages/{msg.id}/")
        assert resp.status_code == 404


@pytest.mark.django_db
class TestResendMessageView:
    def test_resend_permanently_failed(self, authed_client, failed_message):
        resp = authed_client.post(f"/api/v1/messages/{failed_message.id}/resend/")
        assert resp.status_code == 202
        failed_message.refresh_from_db()
        assert failed_message.status == "queued"

    def test_resend_non_failed_returns_400(self, authed_client, message):
        resp = authed_client.post(f"/api/v1/messages/{message.id}/resend/")
        assert resp.status_code == 400


# ── Suppression endpoints ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSuppressionListView:
    url = "/api/v1/suppressions/"

    def test_requires_auth(self, api_client):
        assert api_client.get(self.url).status_code == 401

    def test_lists_suppressions(self, authed_client, bounce, complaint):
        resp = authed_client.get(self.url)
        assert resp.status_code == 200
        assert resp.data["total"] >= 2

    def test_filter_by_type_bounce(self, authed_client, bounce, complaint):
        resp = authed_client.get(self.url + "?type=bounce")
        assert resp.status_code == 200
        for entry in resp.data["suppressions"]:
            assert entry["type"] == "bounce"

    def test_add_manual_suppression(self, authed_client):
        resp = authed_client.post(self.url, {
            "email": "manual@example.com",
            "type": "manual",
            "reason": "spam",
        })
        assert resp.status_code in (200, 201)

    def test_delete_suppression(self, authed_client, bounce):
        resp = authed_client.delete(f"/api/v1/suppressions/{bounce.email}/")
        assert resp.status_code == 204

    def test_delete_nonexistent_returns_404(self, authed_client):
        resp = authed_client.delete("/api/v1/suppressions/nobody@example.com/")
        assert resp.status_code == 404


# ── Stats endpoints ───────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestStatsView:
    url = "/api/v1/stats/"

    def test_requires_auth(self, api_client):
        assert api_client.get(self.url).status_code == 401

    def test_returns_daily_breakdown(self, authed_client):
        resp = authed_client.get(self.url + "?date_range=7d")
        assert resp.status_code == 200
        assert "daily" in resp.data
        assert "totals" in resp.data
        assert len(resp.data["daily"]) == 7

    def test_invalid_date_range_returns_400(self, authed_client):
        resp = authed_client.get(self.url + "?date_from=2030-01-01&date_to=2020-01-01")
        assert resp.status_code == 400

    def test_stats_export_returns_csv(self, authed_client, daily_stats):
        resp = authed_client.get("/api/v1/stats/export/?date_range=7d")
        assert resp.status_code == 200
        assert resp["Content-Type"] == "text/csv"
        assert "date" in resp.content.decode()


# ── Health check ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestHealthEndpoints:
    def test_health_returns_200(self, api_client):
        resp = api_client.get("/health/")
        assert resp.status_code == 200
        assert resp.data["status"] == "ok"

    def test_readiness_returns_200(self, api_client):
        resp = api_client.get("/readiness/")
        assert resp.status_code == 200
        assert "database" in resp.data["checks"]

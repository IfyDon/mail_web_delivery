"""Integration tests for audit-log coverage: the write-logging middleware,
its dashboard-vs-API path coverage, and the retention cleanup task."""
from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.accounts.models import AuditLog


@pytest.fixture
def dashboard_client(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.mark.django_db
class TestAuditMiddlewareCoverage:
    def test_logs_dashboard_write(self, dashboard_client, user):
        dashboard_client.post("/dashboard/webhooks/", {
            "url": "https://example.com/hook", "event_types": ["delivered"],
        })
        assert AuditLog.objects.filter(
            user=user, action__startswith="POST /dashboard/webhooks/",
        ).exists()

    def test_logs_api_write(self, authed_client, user, domain):
        authed_client.post("/api/v1/streams/", {
            "name": "Marketing", "slug": "marketing-audit-test",
        }, format="json")
        assert AuditLog.objects.filter(
            user=user, action__startswith="POST /api/v1/streams/",
        ).exists()

    def test_does_not_log_get_requests(self, dashboard_client, user):
        AuditLog.objects.filter(user=user).delete()
        dashboard_client.get("/dashboard/webhooks/")
        assert not AuditLog.objects.filter(user=user).exists()

    def test_does_not_log_unauthenticated_writes(self):
        AuditLog.objects.all().delete()
        Client().post("/dashboard/webhooks/", {"url": "https://x.com"})
        assert not AuditLog.objects.exists()

    def test_does_not_log_server_errors(self, dashboard_client, user, monkeypatch):
        AuditLog.objects.filter(user=user).delete()

        def _boom(self, request):
            from django.http import HttpResponse
            return HttpResponse(status=500)

        from web.views.webhooks_ui import WebhooksView
        monkeypatch.setattr(WebhooksView, "post", _boom)
        dashboard_client.post("/dashboard/webhooks/", {"url": "https://example.com"})
        assert not AuditLog.objects.filter(user=user).exists()

    def test_records_ip_and_status(self, dashboard_client, user):
        resp = dashboard_client.post(
            "/dashboard/webhooks/",
            {"url": "https://example.com/hook2", "event_types": ["delivered"]},
            REMOTE_ADDR="203.0.113.5",
        )
        entry = AuditLog.objects.filter(user=user).order_by("-created_at").first()
        assert entry is not None
        assert entry.ip_address == "203.0.113.5"
        assert entry.metadata["status_code"] == resp.status_code


@pytest.mark.django_db
class TestAuditLogView:
    def test_shows_only_own_entries(self, dashboard_client, user, second_user):
        AuditLog.objects.create(user=user, action="POST /dashboard/webhooks/")
        AuditLog.objects.create(user=second_user, action="POST /dashboard/domains/")
        resp = dashboard_client.get("/dashboard/audit-log/")
        assert resp.status_code == 200
        entries = list(resp.context["page_obj"])
        assert len(entries) == 1
        assert entries[0].user_id == user.id


@pytest.mark.django_db
class TestCleanupExpiredAuditLogs:
    def test_deletes_old_keeps_recent(self, user):
        from workers.tasks.cleanup_audit_log import cleanup_expired_audit_logs

        old = AuditLog.objects.create(user=user, action="POST /old/")
        AuditLog.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=400)
        )
        recent = AuditLog.objects.create(user=user, action="POST /recent/")

        result = cleanup_expired_audit_logs()
        assert result["deleted"] == 1
        assert not AuditLog.objects.filter(pk=old.pk).exists()
        assert AuditLog.objects.filter(pk=recent.pk).exists()

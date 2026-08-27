"""Integration tests for GDPR self-service data export and account deletion."""
import json
from unittest.mock import patch

import pytest
from django.test import Client

from apps.accounts.models import APIKey, DataExportRequest


@pytest.fixture
def dashboard_client(user):
    """Dashboard views are plain Django views gated by session auth
    (LoginRequiredMixin), not DRF's Authorization-header auth — authed_client's
    Token header has no effect on them, so log in via session instead."""
    client = Client()
    client.force_login(user)
    return client


# ── build_data_export ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestBuildDataExport:
    def test_includes_own_domain_and_message(self, user, domain, message):
        from services.gdpr_service import build_data_export

        content = build_data_export(user)
        data = json.loads(content)
        assert data["account"]["email"] == user.email
        assert any(d["domain"] == domain.domain for d in data["domains"])
        assert any(m["subject"] == message.subject for m in data["messages"])

    def test_excludes_other_users_data(self, user, second_user, domain):
        from apps.domains.models import Domain
        from services.gdpr_service import build_data_export

        Domain.objects.create(
            user=second_user, domain="not-mine.com", verification_status="verified",
        )
        content = build_data_export(user)
        data = json.loads(content)
        domains = {d["domain"] for d in data["domains"]}
        assert "not-mine.com" not in domains

    def test_includes_subscription_and_invoices(self, user):
        from apps.billing.models import Invoice, Plan, Subscription
        from services.gdpr_service import build_data_export

        plan = Plan.objects.create(name="Pro", slug="pro-test-gdpr")
        sub = Subscription.objects.create(user=user, plan=plan, status="active")
        Invoice.objects.create(
            subscription=sub, paystack_reference="ref-gdpr-1", amount_paid=5000, status="paid",
        )
        content = build_data_export(user)
        data = json.loads(content)
        assert data["subscription"]["plan"] == "Pro"
        assert len(data["invoices"]) == 1
        assert data["invoices"][0]["paystack_reference"] == "ref-gdpr-1"


# ── anonymize_and_delete_account ─────────────────────────────────────────────

@pytest.mark.django_db
class TestAnonymizeAndDeleteAccount:
    def test_deletes_owned_content(self, user, domain, message, webhook):
        from apps.domains.models import Domain
        from apps.email_messages.models import Message
        from apps.webhooks.models import Webhook
        from services.gdpr_service import anonymize_and_delete_account

        anonymize_and_delete_account(user)
        assert not Domain.objects.filter(user=user).exists()
        assert not Message.objects.filter(user=user).exists()
        assert not Webhook.objects.filter(user=user).exists()

    def test_anonymizes_user_row(self, user):
        from services.gdpr_service import anonymize_and_delete_account

        original_pk = user.pk
        anonymize_and_delete_account(user)
        user.refresh_from_db()
        assert user.pk == original_pk
        assert user.email.endswith("@deleted.local")
        assert user.first_name == ""
        assert user.is_active is False
        assert not user.has_usable_password()

    def test_preserves_billing_history(self, user):
        from apps.billing.models import Invoice, Plan, Subscription
        from services.gdpr_service import anonymize_and_delete_account

        plan = Plan.objects.create(name="Pro", slug="pro-test-gdpr-2")
        sub = Subscription.objects.create(user=user, plan=plan, status="active")
        invoice = Invoice.objects.create(
            subscription=sub, paystack_reference="ref-gdpr-2", amount_paid=1000, status="paid",
        )
        anonymize_and_delete_account(user)
        assert Subscription.objects.filter(pk=sub.pk).exists()
        assert Invoice.objects.filter(pk=invoice.pk).exists()

    def test_cancels_active_paystack_subscription(self, user, monkeypatch):
        from apps.billing.models import Plan, Subscription
        from services.gdpr_service import anonymize_and_delete_account

        # integrations.paystack.client reads the key straight from os.environ,
        # not Django settings — the `settings` fixture wouldn't reach it.
        monkeypatch.setenv("PAYSTACK_SECRET_KEY", "sk_test_dummy")
        plan = Plan.objects.create(name="Pro", slug="pro-test-gdpr-3")
        sub = Subscription.objects.create(
            user=user, plan=plan, status="active",
            paystack_subscription_code="SUB_123", paystack_email_token="tok_abc",
        )
        with patch("integrations.paystack.client.PaystackClient.disable_subscription") as mock_disable:
            mock_disable.return_value = True
            anonymize_and_delete_account(user)
        mock_disable.assert_called_once_with("SUB_123", "tok_abc")
        sub.refresh_from_db()
        assert sub.status == "cancelled"

    def test_survives_paystack_api_failure(self, user):
        from apps.billing.models import Plan, Subscription
        from services.gdpr_service import anonymize_and_delete_account

        plan = Plan.objects.create(name="Pro", slug="pro-test-gdpr-4")
        Subscription.objects.create(
            user=user, plan=plan, status="active",
            paystack_subscription_code="SUB_456", paystack_email_token="tok_def",
        )
        with patch(
            "integrations.paystack.client.PaystackClient.disable_subscription",
            side_effect=Exception("Paystack is down"),
        ):
            anonymize_and_delete_account(user)  # must not raise
        user.refresh_from_db()
        assert not user.is_active

    def test_deletes_api_keys(self, user):
        from services.gdpr_service import anonymize_and_delete_account

        raw_key, prefix, hashed = APIKey.generate_key()
        APIKey.objects.create(user=user, name="Test Key", prefix=prefix, hashed_key=hashed)
        anonymize_and_delete_account(user)
        assert not APIKey.objects.filter(user=user).exists()

    def test_removes_team_memberships(self, user, second_user):
        from apps.authentication.models import TeamMember
        from services.gdpr_service import anonymize_and_delete_account

        TeamMember.objects.create(
            account_owner=user, email="invitee@example.com", role="viewer", invite_token="tok1",
        )
        TeamMember.objects.create(
            account_owner=second_user, member=user, email=user.email, role="viewer", invite_token="tok2",
        )
        anonymize_and_delete_account(user)
        assert not TeamMember.objects.filter(account_owner=user).exists()
        assert not TeamMember.objects.filter(member=user).exists()


# ── Dashboard views ──────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDataExportViews:
    def test_request_export_enqueues_task(self, dashboard_client, user):
        with patch("workers.tasks.data_export.generate_data_export_task.delay") as mock_delay:
            resp = dashboard_client.post("/dashboard/settings/export/")
        assert resp.status_code == 302
        assert DataExportRequest.objects.filter(user=user).exists()
        mock_delay.assert_called_once()

    def test_duplicate_pending_request_blocked(self, dashboard_client, user):
        DataExportRequest.objects.create(user=user, status=DataExportRequest.STATUS_PENDING)
        with patch("workers.tasks.data_export.generate_data_export_task.delay") as mock_delay:
            dashboard_client.post("/dashboard/settings/export/")
        mock_delay.assert_not_called()
        assert DataExportRequest.objects.filter(user=user).count() == 1

    def test_download_requires_ready_status(self, dashboard_client, user):
        req = DataExportRequest.objects.create(user=user, status=DataExportRequest.STATUS_PROCESSING)
        resp = dashboard_client.get(f"/dashboard/settings/export/{req.pk}/download/")
        assert resp.status_code == 404

    def test_download_ready_export(self, dashboard_client, user):
        from django.core.files.base import ContentFile
        req = DataExportRequest.objects.create(user=user, status=DataExportRequest.STATUS_READY)
        req.file.save("export.json", ContentFile(b'{"ok": true}'), save=True)
        resp = dashboard_client.get(f"/dashboard/settings/export/{req.pk}/download/")
        assert resp.status_code == 200
        assert b"".join(resp.streaming_content) == b'{"ok": true}'
        req.file.delete(save=False)

    def test_cannot_download_other_users_export(self, dashboard_client, second_user):
        from django.core.files.base import ContentFile
        req = DataExportRequest.objects.create(user=second_user, status=DataExportRequest.STATUS_READY)
        req.file.save("export.json", ContentFile(b'{}'), save=True)
        resp = dashboard_client.get(f"/dashboard/settings/export/{req.pk}/download/")
        assert resp.status_code == 404
        req.file.delete(save=False)


@pytest.mark.django_db
class TestAccountDeleteView:
    def test_wrong_password_blocks_deletion(self, dashboard_client, user):
        resp = dashboard_client.post("/dashboard/settings/delete-account/", {
            "password": "wrong-password", "confirm_text": "DELETE",
        })
        assert resp.status_code == 302
        user.refresh_from_db()
        assert user.is_active

    def test_wrong_confirm_text_blocks_deletion(self, user):
        # set_password() rotates the session auth hash, so the client must be
        # logged in *after* the password is set — logging in first (as the
        # shared dashboard_client fixture does) would invalidate the session
        # on the next request and make this pass for the wrong reason.
        user.set_password("correct-password")
        user.save()
        client = Client()
        client.force_login(user)
        resp = client.post("/dashboard/settings/delete-account/", {
            "password": "correct-password", "confirm_text": "delete",
        })
        assert resp.status_code == 302
        user.refresh_from_db()
        assert user.is_active

    def test_correct_confirmation_deletes_account(self, user):
        user.set_password("correct-password")
        user.save()
        client = Client()
        client.force_login(user)
        resp = client.post("/dashboard/settings/delete-account/", {
            "password": "correct-password", "confirm_text": "DELETE",
        })
        assert resp.status_code == 302
        user.refresh_from_db()
        assert not user.is_active
        assert user.email.endswith("@deleted.local")


# ── Celery task ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestGenerateDataExportTask:
    def test_marks_ready_and_saves_file(self, user, domain, celery_eager):
        from workers.tasks.data_export import generate_data_export_task

        req = DataExportRequest.objects.create(user=user)
        generate_data_export_task(req.pk)
        req.refresh_from_db()
        assert req.status == DataExportRequest.STATUS_READY
        assert req.file
        content = json.loads(req.file.read())
        assert content["account"]["email"] == user.email
        req.file.delete(save=False)

    def test_missing_request_returns_error(self, celery_eager):
        from workers.tasks.data_export import generate_data_export_task

        result = generate_data_export_task(999999)
        assert result["status"] == "error"

"""Unit tests for service-layer functions."""
import pytest
from unittest.mock import MagicMock, patch


# ── email_service ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCheckSuppression:
    def test_suppressed_by_bounce(self, bounce):
        from services.email_service import check_suppression
        assert check_suppression(bounce.email) is True

    def test_suppressed_by_complaint(self, complaint):
        from services.email_service import check_suppression
        assert check_suppression(complaint.email) is True

    def test_not_suppressed(self):
        from services.email_service import check_suppression
        assert check_suppression("clean@example.com") is False

    def test_per_user_suppressed(self, suppression, user):
        from services.email_service import check_suppression
        assert check_suppression(suppression.email, user=user) is True

    def test_per_user_not_suppressed(self, user):
        from services.email_service import check_suppression
        assert check_suppression("clean@example.com", user=user) is False

    def test_case_insensitive(self, bounce):
        from services.email_service import check_suppression
        assert check_suppression(bounce.email.upper()) is True


class TestMakeListUnsubscribeHeader:
    def test_without_url(self):
        from services.email_service import make_list_unsubscribe_header
        header = make_list_unsubscribe_header("from@example.com")
        assert "<mailto:from@example.com>" in header

    def test_with_url(self):
        from services.email_service import make_list_unsubscribe_header
        header = make_list_unsubscribe_header(
            "from@example.com",
            unsubscribe_url="https://example.com/unsub/TOKEN",
        )
        assert "<mailto:from@example.com>" in header
        assert "<https://example.com/unsub/TOKEN>" in header

    def test_raises_when_suppressed(self):
        from services.email_service import send_email
        with patch("services.email_service.check_suppression", return_value=True):
            with pytest.raises(ValueError, match="suppressed"):
                send_email("x@x.com", "f@f.com", "Subject", "<p>hi</p>")

    def test_returns_headers_and_payload(self):
        from services.email_service import send_email
        with patch("services.email_service.check_suppression", return_value=False):
            result = send_email("x@x.com", "f@f.com", "Subject", "<p>hi</p>", "hi")
        assert "headers" in result
        assert "payload" in result
        assert result["headers"]["To"] == "x@x.com"
        assert result["headers"]["From"] == "f@f.com"


# ── suppression_service ───────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSuppressionService:
    def test_is_suppressed_true(self, suppression, user):
        from services.suppression_service import is_suppressed
        assert is_suppressed(user, suppression.email) is True

    def test_is_suppressed_false(self, user):
        from services.suppression_service import is_suppressed
        assert is_suppressed(user, "nope@example.com") is False

    def test_is_suppressed_case_insensitive(self, suppression, user):
        from services.suppression_service import is_suppressed
        assert is_suppressed(user, suppression.email.upper()) is True

    def test_add_suppression_creates(self, user):
        from apps.suppressions.models import Suppression
        from services.suppression_service import add_suppression
        obj = add_suppression(user, "new@example.com", Suppression.REASON_BOUNCE)
        assert obj.pk is not None
        assert Suppression.objects.filter(user=user, email="new@example.com").exists()

    def test_add_suppression_idempotent(self, user):
        from apps.suppressions.models import Suppression
        from services.suppression_service import add_suppression
        add_suppression(user, "idem@example.com", Suppression.REASON_BOUNCE)
        add_suppression(user, "idem@example.com", Suppression.REASON_BOUNCE)
        assert Suppression.objects.filter(user=user, email="idem@example.com").count() == 1

    def test_add_suppression_normalises_email(self, user):
        from apps.suppressions.models import Suppression
        from services.suppression_service import add_suppression
        add_suppression(user, "  Upper@Example.COM  ", Suppression.REASON_MANUAL)
        assert Suppression.objects.filter(user=user, email="upper@example.com").exists()


# ── webhook_service ───────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestWebhookService:
    def test_build_event_payload_structure(self):
        from services.webhook_service import build_event_payload
        payload = build_event_payload("delivered", "msg-123", {"key": "val"})
        assert payload["event_type"] == "delivered"
        assert payload["message_id"] == "msg-123"
        assert "timestamp" in payload
        assert payload["metadata"]["key"] == "val"

    def test_build_event_payload_empty_metadata(self):
        from services.webhook_service import build_event_payload
        payload = build_event_payload("bounce", "msg-456")
        assert payload["metadata"] == {}

    def test_trigger_webhooks_enqueues_matching(self, user, webhook):
        from services.webhook_service import build_event_payload, trigger_webhooks
        payload = build_event_payload("delivered", "msg-001")
        with patch("workers.tasks.webhook_dispatch.dispatch_webhook_task.delay") as mock_delay:
            count = trigger_webhooks(user, "delivered", payload)
        assert count == 1
        mock_delay.assert_called_once()

    def test_trigger_webhooks_skips_unsubscribed(self, user, webhook):
        from services.webhook_service import build_event_payload, trigger_webhooks
        payload = build_event_payload("open", "msg-002")
        with patch("workers.tasks.webhook_dispatch.dispatch_webhook_task.delay") as mock_delay:
            count = trigger_webhooks(user, "open", payload)
        assert count == 0
        mock_delay.assert_not_called()

    def test_trigger_webhooks_skips_inactive(self, user, webhook):
        from services.webhook_service import build_event_payload, trigger_webhooks
        webhook.is_active = False
        webhook.save()
        payload = build_event_payload("delivered", "msg-003")
        with patch("workers.tasks.webhook_dispatch.dispatch_webhook_task.delay") as mock_delay:
            count = trigger_webhooks(user, "delivered", payload)
        assert count == 0


# ── analytics_service ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAnalyticsService:
    def test_get_daily_stats_zero_with_no_data(self, user):
        import datetime
        from services.analytics_service import get_daily_stats
        today = datetime.date.today()
        results = get_daily_stats(user, today, today)
        assert len(results) == 1
        assert results[0]["date"] == today.isoformat()
        assert results[0]["sent"] == 0

    def test_get_daily_stats_uses_aggregated_table(self, user, daily_stats):
        import datetime
        from services.analytics_service import get_daily_stats
        today = datetime.date.today()
        results = get_daily_stats(user, today, today)
        assert results[0]["sent"] == 100
        assert results[0]["delivered"] == 95

    def test_get_daily_stats_multi_day_range(self, user):
        import datetime
        from services.analytics_service import get_daily_stats
        today = datetime.date.today()
        week_ago = today - datetime.timedelta(days=6)
        results = get_daily_stats(user, week_ago, today)
        assert len(results) == 7

    def test_get_totals(self, user, daily_stats):
        import datetime
        from services.analytics_service import get_daily_stats, get_totals
        today = datetime.date.today()
        daily = get_daily_stats(user, today, today)
        totals = get_totals(daily)
        assert totals["sent"] == 100
        assert totals["opened"] == 40

    def test_export_stats_csv_columns(self, user, daily_stats):
        import datetime
        from services.analytics_service import export_stats_csv
        today = datetime.date.today()
        csv_str = export_stats_csv(user, today, today)
        assert "date" in csv_str
        assert "sent" in csv_str
        assert "delivered" in csv_str
        assert "opened" in csv_str
        assert "clicked" in csv_str

    def test_export_stats_csv_values(self, user, daily_stats):
        import datetime
        from services.analytics_service import export_stats_csv
        today = datetime.date.today()
        csv_str = export_stats_csv(user, today, today)
        assert "100" in csv_str  # sent
        assert "95" in csv_str   # delivered


# ── billing_service ───────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestBillingService:
    def test_check_quota_passes_within_limit(self, user, quota):
        from services.billing_service import check_quota
        assert check_quota(user) is True

    def test_check_quota_fails_at_limit(self, user, quota):
        from services.billing_service import check_quota
        quota.emails_sent_this_month = quota.monthly_limit
        quota.save()
        assert check_quota(user) is False

    def test_increment_quota(self, user, quota):
        from services.billing_service import increment_quota
        initial = quota.emails_sent_this_month
        increment_quota(user)
        quota.refresh_from_db()
        assert quota.emails_sent_this_month == initial + 1

    def test_check_quota_creates_quota_if_missing(self, user):
        from apps.accounts.models import Quota
        from services.billing_service import check_quota
        Quota.objects.filter(user=user).delete()
        result = check_quota(user)
        assert result is True
        assert Quota.objects.filter(user=user).exists()

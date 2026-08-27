"""Integration tests for Celery tasks (run eagerly — no broker required)."""
import pytest
from unittest.mock import patch, MagicMock


# ── send_email_task ───────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSendEmailTask:
    def test_sends_queued_message(self, message, celery_eager):
        from workers.tasks.send_email import send_email_task
        with patch("workers.tasks.send_email._relay") as mock_relay:
            mock_relay.return_value = {"MessageId": "provider-001"}
            result = send_email_task(str(message.pk))
        assert result["status"] == "sent"
        message.refresh_from_db()
        assert message.status == "sent"
        assert message.provider_message_id == "provider-001"

    def test_marks_suppressed_when_bounced(self, message, bounce, celery_eager):
        # check_suppression(email, user=...) checks the per-user Suppression
        # table, not the raw Bounce table directly — in production this row
        # is created by the SES inbound webhook's _suppress_for_senders()
        # alongside the Bounce record, so recreate that here.
        from apps.suppressions.models import Suppression
        Suppression.objects.create(
            user=message.user, email=bounce.email, reason=Suppression.REASON_BOUNCE,
        )
        message.to_address = bounce.email
        message.save()
        from workers.tasks.send_email import send_email_task
        result = send_email_task(str(message.pk))
        assert result["status"] == "suppressed"
        message.refresh_from_db()
        assert message.status == "suppressed"

    def test_handles_missing_message_gracefully(self, celery_eager):
        import uuid
        from workers.tasks.send_email import send_email_task
        result = send_email_task(str(uuid.uuid4()))
        assert result["status"] == "error"
        assert result["reason"] == "message_not_found"

    def test_skips_already_sent_message(self, sent_message, celery_eager):
        from workers.tasks.send_email import send_email_task
        with patch("workers.tasks.send_email._relay") as mock_relay:
            result = send_email_task(str(sent_message.pk))
        assert result["status"] == "sent"
        mock_relay.assert_not_called()

    def test_relay_failure_triggers_retry(self, message, celery_eager):
        # Calling a bound task directly (not via .apply()/.delay()) is
        # Celery's "called_directly" path: self.retry() can't actually
        # schedule a retry outside a real worker context, so it re-raises.
        # That's expected here — what we're really asserting is that the
        # Message row is correctly marked failed before that propagates.
        from workers.tasks.send_email import send_email_task
        with patch("workers.tasks.send_email._relay", side_effect=Exception("SMTP down")):
            with patch("workers.tasks.webhook_dispatch.dispatch_webhook_task.delay"):
                with pytest.raises(Exception):
                    send_email_task(str(message.pk))
        message.refresh_from_db()
        assert message.status in ("failed", "permanently_failed")

    def test_creates_delivered_event_on_success(self, message, celery_eager):
        from apps.events.models import Event
        from workers.tasks.send_email import send_email_task
        with patch("workers.tasks.send_email._relay") as mock_relay:
            mock_relay.return_value = {"MessageId": "provider-xyz"}
            send_email_task(str(message.pk))
        assert Event.objects.filter(message=message, type=Event.TYPE_DELIVERED).exists()


# ── dispatch_scheduled_messages ───────────────────────────────────────────────

@pytest.mark.django_db
class TestDispatchScheduledMessages:
    def test_dispatches_due_messages(self, scheduled_message, celery_eager):
        from workers.tasks.dispatch_scheduled import dispatch_scheduled_messages
        with patch("workers.tasks.send_email.send_email_task.delay") as mock_delay:
            result = dispatch_scheduled_messages()
        assert result["dispatched"] == 1
        mock_delay.assert_called_once_with(str(scheduled_message.pk))
        scheduled_message.refresh_from_db()
        assert scheduled_message.status == "queued"

    def test_skips_future_messages(self, user, domain, celery_eager):
        from django.utils import timezone
        from apps.email_messages.models import Message
        future_msg = Message.objects.create(
            user=user, domain=domain,
            to_address="r@r.com", from_address="s@s.com",
            subject="Future", html_body="<p>F</p>",
            status=Message.STATUS_SCHEDULED,
            scheduled_at=timezone.now() + timezone.timedelta(hours=1),
        )
        from workers.tasks.dispatch_scheduled import dispatch_scheduled_messages
        with patch("workers.tasks.send_email.send_email_task.delay") as mock_delay:
            result = dispatch_scheduled_messages()
        assert result["dispatched"] == 0
        mock_delay.assert_not_called()

    def test_skips_non_scheduled_messages(self, message, celery_eager):
        from workers.tasks.dispatch_scheduled import dispatch_scheduled_messages
        with patch("workers.tasks.send_email.send_email_task.delay") as mock_delay:
            result = dispatch_scheduled_messages()
        assert result["dispatched"] == 0


# ── reset_monthly_quotas ──────────────────────────────────────────────────────

@pytest.mark.django_db
class TestResetMonthlyQuotas:
    def test_resets_all_quotas(self, user, quota, celery_eager):
        quota.emails_sent_this_month = 500
        quota.save()
        from workers.tasks.reset_quota import reset_monthly_quotas
        reset_monthly_quotas()
        quota.refresh_from_db()
        assert quota.emails_sent_this_month == 0

    def test_multiple_users_reset(self, user, second_user, celery_eager):
        from apps.accounts.models import Quota
        q1 = Quota.objects.create(user=user, emails_sent_this_month=100, monthly_limit=1000)
        q2 = Quota.objects.create(user=second_user, emails_sent_this_month=200, monthly_limit=5000)
        from workers.tasks.reset_quota import reset_monthly_quotas
        reset_monthly_quotas()
        q1.refresh_from_db()
        q2.refresh_from_db()
        assert q1.emails_sent_this_month == 0
        assert q2.emails_sent_this_month == 0

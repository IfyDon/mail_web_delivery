"""Unit tests for Django model methods and properties."""
import pytest
from django.utils import timezone


# ── CustomUser ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCustomUser:
    def test_str(self, user):
        assert str(user) == "test@example.com"

    def test_email_unique(self, user):
        from django.db import IntegrityError
        from apps.accounts.models import CustomUser
        with pytest.raises(IntegrityError):
            CustomUser.objects.create_user(
                username="dup",
                email="test@example.com",
                password="pass",
            )


# ── APIKey ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAPIKey:
    def test_generate_key_format(self):
        from apps.accounts.models import APIKey
        raw, prefix, hashed = APIKey.generate_key()
        assert prefix.startswith("sk_live_")
        assert len(hashed) == 64  # SHA-256 hex
        assert raw.startswith(prefix)

    def test_save_requires_fields(self, user):
        from apps.accounts.models import APIKey
        with pytest.raises(ValueError):
            APIKey(user=user, name="bad").save()

    def test_str(self, api_key):
        assert "sk_live_" in str(api_key)


# ── Quota ─────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestQuota:
    def test_str(self, quota):
        assert "test@example.com" in str(quota)
        assert "10000" in str(quota)


# ── Domain ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDomain:
    def test_is_fully_verified_true(self, domain):
        assert domain.is_fully_verified is True

    def test_is_fully_verified_false(self, unverified_domain):
        assert unverified_domain.is_fully_verified is False

    def test_is_fully_verified_partial(self, domain):
        domain.dmarc_verified = False
        domain.save()
        assert domain.is_fully_verified is False

    def test_get_dns_instructions_keys(self, domain):
        instructions = domain.get_dns_instructions()
        assert set(instructions.keys()) == {"spf", "dkim", "dmarc"}
        for rec in instructions.values():
            assert "record_type" in rec
            assert "host" in rec
            assert "value" in rec

    def test_get_dns_instructions_spf(self, domain):
        instructions = domain.get_dns_instructions()
        assert "v=spf1" in instructions["spf"]["value"]

    def test_str(self, domain):
        assert "example.com" in str(domain)

    def test_unique_together_user_domain(self, user, domain):
        from django.db import IntegrityError
        from apps.domains.models import Domain
        with pytest.raises(IntegrityError):
            Domain.objects.create(user=user, domain="example.com")


# ── Message ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestMessage:
    def test_status_choices_present(self):
        from apps.email_messages.models import Message
        statuses = [c[0] for c in Message.STATUS_CHOICES]
        assert "queued" in statuses
        assert "scheduled" in statuses
        assert "permanently_failed" in statuses
        assert "cancelled" in statuses

    def test_default_status_queued(self, message):
        assert message.status == "queued"

    def test_str(self, message):
        s = str(message)
        assert "sender@example.com" in s
        assert "recipient@example.com" in s

    def test_uuid_primary_key(self, message):
        import uuid
        assert isinstance(message.id, uuid.UUID)

    def test_scheduled_at_nullable(self, message):
        assert message.scheduled_at is None

    def test_scheduled_message_has_scheduled_at(self, scheduled_message):
        assert scheduled_message.status == "scheduled"
        assert scheduled_message.scheduled_at is not None


# ── Suppression ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSuppression:
    def test_unique_user_email(self, suppression, user):
        from django.db import IntegrityError
        from apps.suppressions.models import Suppression
        with pytest.raises(IntegrityError):
            Suppression.objects.create(
                user=user,
                email="suppressed@example.com",
                reason=Suppression.REASON_MANUAL,
            )

    def test_reason_choices(self):
        from apps.suppressions.models import Suppression
        reasons = [c[0] for c in Suppression.REASON_CHOICES]
        assert "bounce" in reasons
        assert "complaint" in reasons
        assert "unsubscribe" in reasons
        assert "manual" in reasons


# ── Webhook ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestWebhook:
    def test_listens_to_subscribed_event(self, webhook):
        assert webhook.listens_to("delivered") is True

    def test_listens_to_unsubscribed_event(self, webhook):
        assert webhook.listens_to("open") is False

    def test_secret_generated(self, webhook):
        assert len(webhook.secret) > 0

    def test_str(self, webhook):
        assert "example.com" in str(webhook)


# ── ContactEngagement ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestContactEngagement:
    def test_apply_open_event(self, user):
        from apps.analytics.models import ContactEngagement
        eng = ContactEngagement(user=user, email="contact@example.com", score=0)
        eng.apply_event("open")
        assert eng.score == 2
        assert eng.open_count == 1
        assert eng.last_open is not None

    def test_apply_click_event(self, user):
        from apps.analytics.models import ContactEngagement
        eng = ContactEngagement(user=user, email="contact@example.com", score=0)
        eng.apply_event("click")
        assert eng.score == 5
        assert eng.click_count == 1

    def test_apply_bounce_event(self, user):
        from apps.analytics.models import ContactEngagement
        eng = ContactEngagement(user=user, email="contact@example.com", score=0)
        eng.apply_event("bounce")
        assert eng.score == -10
        assert eng.bounce_count == 1

    def test_apply_complaint_event(self, user):
        from apps.analytics.models import ContactEngagement
        eng = ContactEngagement(user=user, email="contact@example.com", score=0)
        eng.apply_event("complaint")
        assert eng.score == -50
        assert eng.complaint_count == 1

    def test_apply_unknown_event_noop(self, user):
        from apps.analytics.models import ContactEngagement
        eng = ContactEngagement(user=user, email="contact@example.com", score=10)
        eng.apply_event("unknown_event_type")
        assert eng.score == 10


# ── TeamMember ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTeamMember:
    def test_is_pending_before_accept(self, user, second_user):
        from apps.authentication.models import TeamMember
        tm = TeamMember.objects.create(
            account_owner=user,
            email="invite@example.com",
            role=TeamMember.ROLE_VIEWER,
            invite_token=TeamMember.generate_invite_token(),
        )
        assert tm.is_pending is True

    def test_is_not_pending_after_accept(self, user):
        from apps.authentication.models import TeamMember
        tm = TeamMember.objects.create(
            account_owner=user,
            email="invite@example.com",
            role=TeamMember.ROLE_VIEWER,
            invite_token=TeamMember.generate_invite_token(),
            accepted_at=timezone.now(),
        )
        assert tm.is_pending is False

    def test_is_not_expired_when_fresh(self, user):
        from apps.authentication.models import TeamMember
        tm = TeamMember.objects.create(
            account_owner=user,
            email="invite2@example.com",
            role=TeamMember.ROLE_VIEWER,
            invite_token=TeamMember.generate_invite_token(),
        )
        assert tm.is_expired is False

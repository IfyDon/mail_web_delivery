"""Shared pytest fixtures for all test layers."""
import pytest
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient


# ── Users & Auth ──────────────────────────────────────────────────────────────

@pytest.fixture
def user(db):
    from apps.accounts.models import CustomUser
    u = CustomUser.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
        is_verified=True,
    )
    return u


@pytest.fixture
def second_user(db):
    from apps.accounts.models import CustomUser
    return CustomUser.objects.create_user(
        username="otheruser",
        email="other@example.com",
        password="otherpass123",
        is_verified=True,
    )


@pytest.fixture
def auth_token(db, user):
    token, _ = Token.objects.get_or_create(user=user)
    return token


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authed_client(api_client, auth_token):
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {auth_token.key}")
    return api_client


# ── Account objects ───────────────────────────────────────────────────────────

@pytest.fixture
def quota(db, user):
    from apps.accounts.models import Quota
    quota, _ = Quota.objects.get_or_create(user=user, defaults={"monthly_limit": 10000})
    return quota


@pytest.fixture
def api_key(db, user):
    from apps.accounts.models import APIKey
    raw_key, prefix, hashed = APIKey.generate_key()
    key = APIKey.objects.create(
        user=user,
        name="Test Key",
        prefix=prefix,
        hashed_key=hashed,
    )
    key._raw = raw_key  # attach for use in tests
    return key


# ── Domains ───────────────────────────────────────────────────────────────────

@pytest.fixture
def domain(db, user):
    from apps.domains.models import Domain
    return Domain.objects.create(
        user=user,
        domain="example.com",
        verification_status="verified",
        spf_verified=True,
        dkim_verified=True,
        dmarc_verified=True,
    )


@pytest.fixture
def unverified_domain(db, user):
    from apps.domains.models import Domain
    return Domain.objects.create(
        user=user,
        domain="unverified.com",
        verification_status="unverified",
    )


# ── Messages ──────────────────────────────────────────────────────────────────

@pytest.fixture
def message(db, user, domain):
    from apps.email_messages.models import Message
    return Message.objects.create(
        user=user,
        domain=domain,
        to_address="recipient@example.com",
        from_address="sender@example.com",
        subject="Test Subject",
        html_body="<p>Hello</p>",
        text_body="Hello",
        status=Message.STATUS_QUEUED,
    )


@pytest.fixture
def sent_message(db, user, domain):
    from apps.email_messages.models import Message
    return Message.objects.create(
        user=user,
        domain=domain,
        to_address="recipient@example.com",
        from_address="sender@example.com",
        subject="Sent Message",
        html_body="<p>Sent</p>",
        status=Message.STATUS_SENT,
    )


@pytest.fixture
def failed_message(db, user, domain):
    from apps.email_messages.models import Message
    return Message.objects.create(
        user=user,
        domain=domain,
        to_address="recipient@example.com",
        from_address="sender@example.com",
        subject="Failed Message",
        html_body="<p>Failed</p>",
        status=Message.STATUS_PERMANENTLY_FAILED,
        attempts=5,
    )


@pytest.fixture
def scheduled_message(db, user, domain):
    from apps.email_messages.models import Message
    return Message.objects.create(
        user=user,
        domain=domain,
        to_address="recipient@example.com",
        from_address="sender@example.com",
        subject="Scheduled Message",
        html_body="<p>Scheduled</p>",
        status=Message.STATUS_SCHEDULED,
        scheduled_at=timezone.now() - timezone.timedelta(minutes=5),
    )


# ── Suppression ───────────────────────────────────────────────────────────────

@pytest.fixture
def suppression(db, user):
    from apps.suppressions.models import Suppression
    return Suppression.objects.create(
        user=user,
        email="suppressed@example.com",
        reason=Suppression.REASON_BOUNCE,
    )


@pytest.fixture
def bounce(db):
    from apps.suppressions.models import Bounce
    return Bounce.objects.create(email="bounced@example.com", reason="Mailbox full")


@pytest.fixture
def complaint(db):
    from apps.suppressions.models import Complaint
    return Complaint.objects.create(email="complained@example.com", feedback_type="abuse")


# ── Events ────────────────────────────────────────────────────────────────────

@pytest.fixture
def open_event(db, sent_message):
    from apps.events.models import Event
    return Event.objects.create(
        message=sent_message,
        type=Event.TYPE_OPEN,
        metadata={"ip": "1.2.3.4"},
    )


@pytest.fixture
def click_event(db, sent_message):
    from apps.events.models import Event
    return Event.objects.create(
        message=sent_message,
        type=Event.TYPE_CLICK,
        metadata={"url": "https://example.com", "ip": "1.2.3.4"},
    )


# ── Webhooks ──────────────────────────────────────────────────────────────────

@pytest.fixture
def webhook(db, user):
    from apps.webhooks.models import Webhook
    return Webhook.objects.create(
        user=user,
        url="https://example.com/webhook/",
        event_types=["delivered", "bounce", "complaint"],
        is_active=True,
    )


# ── Analytics ─────────────────────────────────────────────────────────────────

@pytest.fixture
def daily_stats(db, user):
    from apps.analytics.models import DailyStats
    import datetime
    return DailyStats.objects.create(
        user=user,
        date=datetime.date.today(),
        sent=100,
        delivered=95,
        opened=40,
        clicked=10,
        bounced=3,
        complained=1,
    )


# ── Celery ────────────────────────────────────────────────────────────────────

@pytest.fixture
def celery_eager(settings):
    """Run Celery tasks synchronously (no broker needed)."""
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

"""GDPR self-service: export everything a user owns, or erase their personal data.

Deletion anonymizes the CustomUser row rather than hard-deleting it, so
billing records (Subscription/Invoice) survive for tax/legal retention —
GDPR Art. 17(3)(b) permits keeping data needed to comply with a legal
obligation. Everything else the user owns is hard-deleted.
"""
import json
import logging
import uuid
from datetime import date, datetime

from django.core.files.base import ContentFile
from django.utils import timezone

logger = logging.getLogger(__name__)


def _json_default(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def build_data_export(user) -> bytes:
    """Serialize everything the user owns to a single JSON document."""
    from apps.accounts.models import APIKey, IPWhitelist
    from apps.authentication.models import TeamMember
    from apps.billing.models import Invoice, Subscription
    from apps.domains.models import Domain
    from apps.email_messages.models import Message
    from apps.email_templates.models import Template
    from apps.inbound.models import InboundMessage, InboundRoute
    from apps.streams.models import Stream
    from apps.suppressions.models import Suppression
    from apps.webhooks.models import Webhook

    data = {
        "exported_at": timezone.now().isoformat(),
        "account": {
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "date_joined": user.date_joined,
            "is_verified": user.is_verified,
        },
        "domains": list(
            Domain.objects.filter(user=user).values(
                "domain", "verification_status", "spf_verified", "dkim_verified",
                "dmarc_verified", "created_at", "verified_at",
            )
        ),
        "messages": list(
            Message.objects.filter(user=user).values(
                "id", "to_address", "from_address", "reply_to", "cc_addresses",
                "bcc_addresses", "subject", "html_body", "text_body", "status",
                "stream", "provider_message_id", "created_at",
            )
        ),
        "inbound_messages": list(
            InboundMessage.objects.filter(user=user).values(
                "id", "from_address", "to_address", "subject", "text_body",
                "html_body", "status", "received_at",
            )
        ),
        "inbound_routes": list(
            InboundRoute.objects.filter(user=user).values(
                "id", "domain__domain", "match_type", "local_part", "is_active", "created_at",
            )
        ),
        "templates": list(
            Template.objects.filter(user=user).values(
                "id", "name", "slug", "description", "subject", "created_at", "updated_at",
            )
        ),
        "webhooks": list(
            Webhook.objects.filter(user=user).values(
                "id", "url", "event_types", "is_active", "created_at",
            )
        ),
        "suppressions": list(
            Suppression.objects.filter(user=user).values("email", "reason", "created_at")
        ),
        "streams": list(
            Stream.objects.filter(user=user).values(
                "name", "slug", "description", "is_active", "created_at",
            )
        ),
        "api_keys": list(
            APIKey.objects.filter(user=user).values(
                "name", "prefix", "rate_limit", "is_active", "created_at", "last_used_at",
            )
        ),
        "ip_whitelist": list(
            IPWhitelist.objects.filter(user=user).values("ip_address", "label", "created_at")
        ),
        "team_members_invited": list(
            TeamMember.objects.filter(account_owner=user).values(
                "email", "role", "invited_at", "accepted_at",
            )
        ),
        "subscription": None,
        "invoices": [],
    }

    subscription = Subscription.objects.filter(user=user).first()
    if subscription:
        data["subscription"] = {
            "plan": subscription.plan.name,
            "status": subscription.status,
            "current_period_start": subscription.current_period_start,
            "current_period_end": subscription.current_period_end,
            "created_at": subscription.created_at,
        }
        data["invoices"] = list(
            Invoice.objects.filter(subscription=subscription).values(
                "paystack_reference", "amount_paid", "currency", "status",
                "period_start", "period_end", "created_at",
            )
        )

    return json.dumps(data, indent=2, default=_json_default).encode("utf-8")


def anonymize_and_delete_account(user) -> None:
    """Erase a user's personal data and hard-delete everything they own,
    except billing history (kept, tied to the now-anonymized account)."""
    from apps.accounts.models import APIKey, IdempotencyKey, IPWhitelist
    from apps.authentication.models import TeamMember
    from apps.billing.models import Subscription
    from apps.domains.models import Domain
    from apps.email_messages.models import Message
    from apps.email_templates.models import Template
    from apps.inbound.models import InboundMessage, InboundRoute
    from apps.streams.models import Stream
    from apps.suppressions.models import Suppression
    from apps.webhooks.models import Webhook

    subscription = Subscription.objects.filter(user=user, status__in=(
        Subscription.STATUS_ACTIVE, Subscription.STATUS_TRIALING,
    )).first()
    if subscription and subscription.paystack_subscription_code:
        try:
            from integrations.paystack.client import PaystackClient
            PaystackClient().disable_subscription(
                subscription.paystack_subscription_code, subscription.paystack_email_token,
            )
            subscription.status = Subscription.STATUS_CANCELLED
            subscription.save(update_fields=["status"])
        except Exception:  # noqa: BLE001 — best-effort; don't block deletion on Paystack downtime
            logger.exception("gdpr: failed to cancel Paystack subscription for user=%s", user.pk)

    Message.objects.filter(user=user).delete()
    InboundMessage.objects.filter(user=user).delete()
    InboundRoute.objects.filter(user=user).delete()
    Domain.objects.filter(user=user).delete()
    Template.objects.filter(user=user).delete()
    Webhook.objects.filter(user=user).delete()
    Suppression.objects.filter(user=user).delete()
    Stream.objects.filter(user=user).delete()
    APIKey.objects.filter(user=user).delete()
    IdempotencyKey.objects.filter(user=user).delete()
    IPWhitelist.objects.filter(user=user).delete()
    TeamMember.objects.filter(account_owner=user).delete()
    TeamMember.objects.filter(member=user).delete()

    placeholder = f"deleted-{uuid.uuid4().hex}@deleted.local"
    user.email = placeholder
    user.username = placeholder
    user.first_name = ""
    user.last_name = ""
    user.is_active = False
    user.is_verified = False
    user.set_unusable_password()
    user.save()

    logger.info("gdpr: anonymized and erased data for user=%s", user.pk)


def save_export_file(export_request, content: bytes) -> None:
    export_request.file.save(
        f"export-{export_request.user_id}-{export_request.pk}.json",
        ContentFile(content),
        save=False,
    )
    export_request.status = export_request.STATUS_READY
    export_request.completed_at = timezone.now()
    export_request.save(update_fields=["file", "status", "completed_at"])

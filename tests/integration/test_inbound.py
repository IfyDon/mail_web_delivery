"""Integration tests for inbound email routing: routes API, message API,
MIME parsing, and the SES SNS ingestion webhook."""
import json
from unittest.mock import patch

import pytest

from apps.inbound.models import InboundMessage, InboundRoute


# ── InboundRoute API ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestInboundRouteAPI:
    def test_create_wildcard_route(self, authed_client, domain):
        resp = authed_client.post(
            "/api/v1/inbound/routes/",
            {"domain": domain.id, "match_type": "wildcard"},
            format="json",
        )
        assert resp.status_code == 201, resp.data
        assert resp.data["address"] == f"*@{domain.domain}"

    def test_create_exact_route(self, authed_client, domain):
        resp = authed_client.post(
            "/api/v1/inbound/routes/",
            {"domain": domain.id, "match_type": "exact", "local_part": "support"},
            format="json",
        )
        assert resp.status_code == 201, resp.data
        assert resp.data["address"] == f"support@{domain.domain}"

    def test_exact_route_requires_local_part(self, authed_client, domain):
        resp = authed_client.post(
            "/api/v1/inbound/routes/",
            {"domain": domain.id, "match_type": "exact"},
            format="json",
        )
        assert resp.status_code == 400
        assert resp.data["errors"][0]["field"] == "local_part"

    def test_wildcard_route_rejects_local_part(self, authed_client, domain):
        resp = authed_client.post(
            "/api/v1/inbound/routes/",
            {"domain": domain.id, "match_type": "wildcard", "local_part": "support"},
            format="json",
        )
        assert resp.status_code == 400
        assert resp.data["errors"][0]["field"] == "local_part"

    def test_cannot_use_unverified_domain(self, authed_client, unverified_domain):
        resp = authed_client.post(
            "/api/v1/inbound/routes/",
            {"domain": unverified_domain.id, "match_type": "wildcard"},
            format="json",
        )
        assert resp.status_code == 400
        assert resp.data["errors"][0]["field"] == "domain"

    def test_cannot_use_other_users_domain(self, authed_client, second_user):
        from apps.domains.models import Domain
        other_domain = Domain.objects.create(
            user=second_user, domain="other.com", verification_status="verified",
        )
        resp = authed_client.post(
            "/api/v1/inbound/routes/",
            {"domain": other_domain.id, "match_type": "wildcard"},
            format="json",
        )
        assert resp.status_code == 400
        assert resp.data["errors"][0]["field"] == "domain"

    def test_list_only_returns_own_routes(self, authed_client, domain, second_user):
        from apps.domains.models import Domain
        InboundRoute.objects.create(user=domain.user, domain=domain, match_type="wildcard")
        other_domain = Domain.objects.create(
            user=second_user, domain="other2.com", verification_status="verified",
        )
        InboundRoute.objects.create(user=second_user, domain=other_domain, match_type="wildcard")

        resp = authed_client.get("/api/v1/inbound/routes/")
        assert resp.status_code == 200
        assert resp.data["count"] == 1

    def test_delete_route(self, authed_client, domain):
        route = InboundRoute.objects.create(user=domain.user, domain=domain, match_type="wildcard")
        resp = authed_client.delete(f"/api/v1/inbound/routes/{route.id}/")
        assert resp.status_code == 204
        assert not InboundRoute.objects.filter(pk=route.id).exists()


# ── InboundMessage API ───────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestInboundMessageAPI:
    def test_list_only_returns_own_messages(self, authed_client, user, second_user, domain):
        route = InboundRoute.objects.create(user=user, domain=domain, match_type="wildcard")
        InboundMessage.objects.create(
            user=user, route=route, from_address="a@x.com", to_address="b@example.com",
            subject="Mine",
        )
        InboundMessage.objects.create(
            user=second_user, from_address="a@x.com", to_address="c@other.com", subject="Not mine",
        )
        resp = authed_client.get("/api/v1/inbound/messages/")
        assert resp.status_code == 200
        assert resp.data["count"] == 1
        assert resp.data["results"][0]["subject"] == "Mine"

    def test_retrieve_message_with_attachments(self, authed_client, user, domain):
        from django.core.files.base import ContentFile
        from apps.inbound.models import InboundAttachment

        route = InboundRoute.objects.create(user=user, domain=domain, match_type="wildcard")
        msg = InboundMessage.objects.create(
            user=user, route=route, from_address="a@x.com", to_address="b@example.com",
            subject="Has attachment", text_body="hi",
        )
        InboundAttachment.objects.create(
            message=msg, file=ContentFile(b"data", name="f.txt"),
            filename="f.txt", content_type="text/plain", size=4,
        )
        resp = authed_client.get(f"/api/v1/inbound/messages/{msg.id}/")
        assert resp.status_code == 200
        assert resp.data["text_body"] == "hi"
        assert len(resp.data["attachments"]) == 1
        assert resp.data["attachments"][0]["filename"] == "f.txt"

    def test_status_filter(self, authed_client, user, domain):
        route = InboundRoute.objects.create(user=user, domain=domain, match_type="wildcard")
        InboundMessage.objects.create(
            user=user, route=route, from_address="a@x.com", to_address="b@example.com",
            status=InboundMessage.STATUS_ROUTED,
        )
        InboundMessage.objects.create(
            user=user, route=route, from_address="a@x.com", to_address="b@example.com",
            status=InboundMessage.STATUS_FORWARDED,
        )
        resp = authed_client.get("/api/v1/inbound/messages/?status=forwarded")
        assert resp.status_code == 200
        assert resp.data["count"] == 1
        assert resp.data["results"][0]["status"] == "forwarded"


# ── MIME parsing ──────────────────────────────────────────────────────────────

class TestParseRawEmail:
    def test_parses_multipart_text_html_and_attachment(self):
        from services.inbound_service import parse_raw_email

        raw = (
            b'From: sender@example.com\r\n'
            b'To: support@example.com\r\n'
            b'Subject: Hello there\r\n'
            b'Content-Type: multipart/mixed; boundary="AAA"\r\n\r\n'
            b'--AAA\r\n'
            b'Content-Type: multipart/alternative; boundary="BBB"\r\n\r\n'
            b'--BBB\r\n'
            b'Content-Type: text/plain; charset="utf-8"\r\n\r\n'
            b'Plain text body\r\n'
            b'--BBB\r\n'
            b'Content-Type: text/html; charset="utf-8"\r\n\r\n'
            b'<p>HTML body</p>\r\n'
            b'--BBB--\r\n'
            b'--AAA\r\n'
            b'Content-Type: text/plain; name="note.txt"\r\n'
            b'Content-Disposition: attachment; filename="note.txt"\r\n\r\n'
            b'attachment contents\r\n'
            b'--AAA--\r\n'
        )
        parsed = parse_raw_email(raw)
        assert parsed["from_address"] == "sender@example.com"
        assert parsed["subject"] == "Hello there"
        assert "Plain text body" in parsed["text_body"]
        assert "<p>HTML body</p>" in parsed["html_body"]
        assert len(parsed["attachments"]) == 1
        assert parsed["attachments"][0]["filename"] == "note.txt"
        assert parsed["attachments"][0]["content"] == b"attachment contents\r\n" or \
            parsed["attachments"][0]["content"].strip() == b"attachment contents"

    def test_parses_simple_plain_text_message(self):
        from services.inbound_service import parse_raw_email

        raw = (
            b'From: "Jane Doe" <jane@example.com>\r\n'
            b'To: hello@example.com\r\n'
            b'Subject: Simple\r\n'
            b'Content-Type: text/plain; charset="utf-8"\r\n\r\n'
            b'Just plain text.\r\n'
        )
        parsed = parse_raw_email(raw)
        assert parsed["from_address"] == "jane@example.com"
        assert "Just plain text." in parsed["text_body"]
        assert parsed["html_body"] == ""
        assert parsed["attachments"] == []


# ── Routing logic ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestRouteInboundEmail:
    def test_exact_route_wins_over_wildcard(self, user, domain):
        InboundRoute.objects.create(user=user, domain=domain, match_type="wildcard")
        exact = InboundRoute.objects.create(
            user=user, domain=domain, match_type="exact", local_part="support",
        )
        from services.inbound_service import find_route
        found = find_route(f"support@{domain.domain}")
        assert found.pk == exact.pk

    def test_falls_back_to_wildcard(self, user, domain):
        wildcard = InboundRoute.objects.create(user=user, domain=domain, match_type="wildcard")
        from services.inbound_service import find_route
        found = find_route(f"anything@{domain.domain}")
        assert found.pk == wildcard.pk

    def test_no_route_returns_none(self, domain):
        from services.inbound_service import find_route
        assert find_route(f"nobody@{domain.domain}") is None

    def test_creates_message_and_dispatches_webhook(self, user, domain, webhook, celery_eager):
        webhook.event_types = ["inbound"]
        webhook.save()
        InboundRoute.objects.create(user=user, domain=domain, match_type="wildcard")

        from services.inbound_service import route_inbound_email
        with patch("workers.tasks.webhook_dispatch.dispatch_webhook_task.delay") as mock_delay:
            created = route_inbound_email(
                ses_message_id="ses-abc-123",
                recipients=[f"hello@{domain.domain}"],
                receipt={"spamVerdict": {"status": "PASS"}, "virusVerdict": {"status": "PASS"}},
                parsed={
                    "from_address": "someone@outside.com", "subject": "Hi",
                    "text_body": "body", "html_body": "", "headers": {}, "attachments": [],
                },
            )
        assert len(created) == 1
        msg = created[0]
        assert msg.status == InboundMessage.STATUS_FORWARDED
        assert msg.user_id == user.id
        assert msg.spam_verdict == "PASS"
        mock_delay.assert_called_once()

    def test_unrouted_recipient_creates_stub_without_user(self, domain):
        from services.inbound_service import route_inbound_email

        created = route_inbound_email(
            ses_message_id="ses-def-456",
            recipients=[f"nobody@{domain.domain}"],
            receipt={},
            parsed={
                "from_address": "someone@outside.com", "subject": "Hi",
                "text_body": "", "html_body": "", "headers": {}, "attachments": [],
            },
        )
        assert len(created) == 0
        stub = InboundMessage.objects.get(ses_message_id="ses-def-456")
        assert stub.status == InboundMessage.STATUS_UNROUTED
        assert stub.user is None

    def test_no_matching_webhook_leaves_status_routed(self, user, domain, celery_eager):
        InboundRoute.objects.create(user=user, domain=domain, match_type="wildcard")
        from services.inbound_service import route_inbound_email

        created = route_inbound_email(
            ses_message_id="ses-ghi-789",
            recipients=[f"hello@{domain.domain}"],
            receipt={},
            parsed={
                "from_address": "someone@outside.com", "subject": "Hi",
                "text_body": "", "html_body": "", "headers": {}, "attachments": [],
            },
        )
        assert created[0].status == InboundMessage.STATUS_ROUTED


# ── SES SNS ingestion webhook ─────────────────────────────────────────────────

@pytest.mark.django_db
class TestSESInboundEmailView:
    def test_unsigned_notification_rejected(self, api_client):
        """No SNS signature at all → rejected before any processing."""
        resp = api_client.post(
            "/api/v1/webhooks/ses-inbound-email/",
            json.dumps({
                "Type": "Notification",
                "Message": json.dumps({"notificationType": "Bounce"}),
            }),
            content_type="application/json",
        )
        assert resp.status_code == 403

    def test_untrusted_signing_cert_host_rejected(self, api_client):
        """SigningCertURL pointing off AWS's domain → rejected, cert never fetched."""
        with patch("api.v1.views.ses_inbound_email.urllib.request.urlopen") as mock_open:
            resp = api_client.post(
                "/api/v1/webhooks/ses-inbound-email/",
                json.dumps({
                    "Type": "Notification",
                    "Message": json.dumps({"notificationType": "Bounce"}),
                    "MessageId": "id-1",
                    "TopicArn": "arn:aws:sns:us-east-1:123:t",
                    "Timestamp": "2024-01-01T00:00:00Z",
                    "Signature": "ZmFrZQ==",
                    "SigningCertURL": "https://sns.attacker.com/cert.pem",
                }),
                content_type="application/json",
            )
        assert resp.status_code == 403
        mock_open.assert_not_called()

    def test_subscription_confirmation_hits_subscribe_url(self, api_client):
        with patch(
            "api.v1.views.ses_inbound_email.verify_sns_message", return_value=True,
        ), patch("api.v1.views.ses_inbound_email.urllib.request.urlopen") as mock_open:
            resp = api_client.post(
                "/api/v1/webhooks/ses-inbound-email/",
                json.dumps({
                    "Type": "SubscriptionConfirmation",
                    "SubscribeURL": "https://sns.us-east-1.amazonaws.com/confirm",
                }),
                content_type="application/json",
            )
        assert resp.status_code == 200
        assert resp.data["status"] == "confirmed"
        mock_open.assert_called_once()

    def test_ignores_non_received_notification(self, api_client):
        with patch("api.v1.views.ses_inbound_email.verify_sns_message", return_value=True):
            resp = api_client.post(
                "/api/v1/webhooks/ses-inbound-email/",
                json.dumps({
                    "Type": "Notification",
                    "Message": json.dumps({"notificationType": "Bounce"}),
                }),
                content_type="application/json",
            )
        assert resp.status_code == 200
        assert resp.data["status"] == "ignored"

    def test_invalid_json_returns_400(self, api_client):
        resp = api_client.post(
            "/api/v1/webhooks/ses-inbound-email/", "not json", content_type="application/json",
        )
        assert resp.status_code == 400

    def test_received_notification_fetches_and_routes(self, api_client, user, domain, settings):
        settings.AWS_SES_INBOUND_BUCKET = "test-bucket"
        InboundRoute.objects.create(user=user, domain=domain, match_type="wildcard")

        raw_email = (
            b'From: sender@outside.com\r\n'
            b'Subject: Ingested\r\n'
            b'Content-Type: text/plain; charset="utf-8"\r\n\r\n'
            b'Hello world\r\n'
        )
        notification = {
            "Type": "Notification",
            "Message": json.dumps({
                "notificationType": "Received",
                "mail": {"messageId": "ses-xyz-999", "destination": [f"hi@{domain.domain}"]},
                "receipt": {
                    "recipients": [f"hi@{domain.domain}"],
                    "spamVerdict": {"status": "PASS"},
                    "virusVerdict": {"status": "PASS"},
                },
            }),
        }
        with patch(
            "api.v1.views.ses_inbound_email.fetch_raw_email", return_value=raw_email,
        ) as mock_fetch, patch(
            "api.v1.views.ses_inbound_email.verify_sns_message", return_value=True,
        ):
            resp = api_client.post(
                "/api/v1/webhooks/ses-inbound-email/",
                json.dumps(notification),
                content_type="application/json",
            )
        assert resp.status_code == 200
        mock_fetch.assert_called_once_with("test-bucket", "inbound/ses-xyz-999")
        msg = InboundMessage.objects.get(ses_message_id="ses-xyz-999")
        assert msg.subject == "Ingested"
        assert "Hello world" in msg.text_body


# ── SES bounce/complaint SNS webhook ──────────────────────────────────────────

@pytest.mark.django_db
class TestSESInboundView:
    def test_unsigned_notification_rejected(self, api_client):
        resp = api_client.post(
            "/api/v1/webhooks/ses/",
            json.dumps({
                "Type": "Notification",
                "Message": json.dumps({
                    "notificationType": "Bounce",
                    "bounce": {
                        "bounceType": "Permanent",
                        "bouncedRecipients": [{"emailAddress": "victim@example.com"}],
                    },
                }),
            }),
            content_type="application/json",
        )
        assert resp.status_code == 403

    def test_forged_bounce_does_not_create_suppression(self, api_client, user, message):
        """A forged, unsigned Bounce notification must not reach the handler
        that would otherwise suppress the address platform-wide."""
        from apps.suppressions.models import Suppression

        resp = api_client.post(
            "/api/v1/webhooks/ses/",
            json.dumps({
                "Type": "Notification",
                "Message": json.dumps({
                    "notificationType": "Bounce",
                    "bounce": {
                        "bounceType": "Permanent",
                        "bouncedRecipients": [{"emailAddress": message.to_address}],
                    },
                }),
            }),
            content_type="application/json",
        )
        assert resp.status_code == 403
        assert not Suppression.objects.filter(email=message.to_address).exists()

    def test_verified_bounce_suppresses_recipient(self, api_client, user, message):
        from apps.suppressions.models import Suppression

        with patch("api.v1.views.ses_inbound.verify_sns_message", return_value=True):
            resp = api_client.post(
                "/api/v1/webhooks/ses/",
                json.dumps({
                    "Type": "Notification",
                    "Message": json.dumps({
                        "notificationType": "Bounce",
                        "bounce": {
                            "bounceType": "Permanent",
                            "bouncedRecipients": [{"emailAddress": message.to_address}],
                        },
                    }),
                }),
                content_type="application/json",
            )
        assert resp.status_code == 200
        assert Suppression.objects.filter(email=message.to_address, user=user).exists()

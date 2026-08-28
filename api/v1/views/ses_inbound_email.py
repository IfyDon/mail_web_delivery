"""Inbound AWS SNS handler for received mail (SES receipt rule: S3 + SNS actions).

The receipt rule stores the raw MIME message in S3 under
AWS_SES_INBOUND_PREFIX + <ses-message-id>, then publishes an SNS
notification here with the envelope (recipients, spam/virus verdicts) so we
know which object to fetch and how to route it.
"""
import json
import logging
import urllib.request

from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from integrations.ses.sns_verify import is_trusted_aws_url, verify_sns_message
from services.inbound_service import fetch_raw_email, parse_raw_email, route_inbound_email

logger = logging.getLogger(__name__)


class SESInboundEmailView(APIView):
    """POST /api/v1/webhooks/ses-inbound-email/

    Receives SNS notifications from AWS for received (inbound) mail.
    No API-key auth — SNS delivers unauthenticated; we verify the SNS signature.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return Response({"error": "Invalid JSON"}, status=400)

        if not verify_sns_message(body):
            return Response({"error": "Invalid signature"}, status=403)

        msg_type = body.get("Type", "")

        if msg_type == "SubscriptionConfirmation":
            subscribe_url = body.get("SubscribeURL", "")
            if is_trusted_aws_url(subscribe_url):
                try:
                    urllib.request.urlopen(subscribe_url, timeout=5)  # noqa: S310
                    logger.info("ses_inbound_email: SNS subscription confirmed")
                except Exception as exc:
                    logger.error("ses_inbound_email: subscription confirmation failed: %s", exc)
            return Response({"status": "confirmed"})

        if msg_type != "Notification":
            return Response({"status": "ignored"})

        try:
            message = json.loads(body.get("Message", "{}"))
        except (json.JSONDecodeError, ValueError):
            return Response({"error": "Invalid Message JSON"}, status=400)

        if message.get("notificationType") != "Received":
            return Response({"status": "ignored"})

        mail = message.get("mail", {})
        receipt = message.get("receipt", {})
        ses_message_id = mail.get("messageId", "")
        recipients = receipt.get("recipients", []) or mail.get("destination", [])

        if not ses_message_id or not recipients:
            logger.warning("ses_inbound_email: missing messageId/recipients")
            return Response({"status": "ignored"})

        if receipt.get("action", {}).get("type") != "S3" and not settings.AWS_SES_INBOUND_BUCKET:
            logger.error("ses_inbound_email: AWS_SES_INBOUND_BUCKET not configured")
            return Response({"status": "error"}, status=500)

        try:
            key = f"{settings.AWS_SES_INBOUND_PREFIX}{ses_message_id}"
            raw = fetch_raw_email(settings.AWS_SES_INBOUND_BUCKET, key)
            parsed = parse_raw_email(raw)
        except Exception as exc:  # noqa: BLE001 — S3/parse failures shouldn't crash the SNS webhook
            logger.error("ses_inbound_email: failed to fetch/parse %s: %s", ses_message_id, exc)
            return Response({"status": "error"}, status=500)

        route_inbound_email(
            ses_message_id=ses_message_id,
            recipients=recipients,
            receipt=receipt,
            parsed=parsed,
        )

        return Response({"status": "ok"})

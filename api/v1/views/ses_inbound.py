"""Inbound AWS SNS handler for SES bounce and complaint notifications."""

import hashlib
import json
import logging
import urllib.request

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

logger = logging.getLogger(__name__)


class SESInboundView(APIView):
    """POST /api/v1/webhooks/ses/

    Receives SNS notifications from AWS for SES bounces and complaints.
    No API-key auth — SNS delivers unauthenticated; we verify the SNS signature.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return Response({"error": "Invalid JSON"}, status=400)

        msg_type = body.get("Type", "")

        # SNS subscription confirmation — fetch the SubscribeURL to confirm
        if msg_type == "SubscriptionConfirmation":
            subscribe_url = body.get("SubscribeURL", "")
            if subscribe_url.startswith("https://sns."):
                try:
                    urllib.request.urlopen(subscribe_url, timeout=5)  # noqa: S310
                    logger.info("ses_inbound: SNS subscription confirmed")
                except Exception as exc:
                    logger.error("ses_inbound: subscription confirmation failed: %s", exc)
            return Response({"status": "confirmed"})

        if msg_type != "Notification":
            return Response({"status": "ignored"})

        # Parse the inner SES message
        try:
            message = json.loads(body.get("Message", "{}"))
        except (json.JSONDecodeError, ValueError):
            return Response({"error": "Invalid Message JSON"}, status=400)

        notification_type = message.get("notificationType", "")

        if notification_type == "Bounce":
            self._handle_bounce(message)
        elif notification_type == "Complaint":
            self._handle_complaint(message)
        else:
            logger.debug("ses_inbound: unhandled notificationType=%s", notification_type)

        return Response({"status": "ok"})

    def _handle_bounce(self, message: dict) -> None:
        bounce = message.get("bounce", {})
        if bounce.get("bounceType") != "Permanent":
            return  # only suppress hard (permanent) bounces

        from apps.suppressions.models import Bounce as BounceRecord, Suppression
        from apps.email_messages.models import Message

        for recipient in bounce.get("bouncedRecipients", []):
            email = recipient.get("emailAddress", "").lower().strip()
            if not email:
                continue

            # Store raw bounce record
            BounceRecord.objects.create(
                email=email,
                reason=recipient.get("diagnosticCode", ""),
                smtp_code=recipient.get("status", ""),
                raw=json.dumps(message),
            )

            # Suppress for every user who has recently sent to this address
            self._suppress_for_senders(email, Suppression.REASON_BOUNCE)
            logger.info("ses_inbound: hard bounce suppressed %s", email)

    def _handle_complaint(self, message: dict) -> None:
        from apps.suppressions.models import Complaint as ComplaintRecord, Suppression
        complaint = message.get("complaint", {})

        for recipient in complaint.get("complainedRecipients", []):
            email = recipient.get("emailAddress", "").lower().strip()
            if not email:
                continue

            ComplaintRecord.objects.create(
                email=email,
                feedback_type=complaint.get("complaintFeedbackType", ""),
                raw=json.dumps(message),
            )

            self._suppress_for_senders(email, Suppression.REASON_COMPLAINT)
            logger.info("ses_inbound: complaint suppressed %s", email)

    @staticmethod
    def _suppress_for_senders(email: str, reason: str) -> None:
        """Add a Suppression record for every user who has sent to *email*."""
        from apps.email_messages.models import Message
        from services.suppression_service import add_suppression

        user_ids = (
            Message.objects
            .filter(to_address__iexact=email)
            .values_list("user_id", flat=True)
            .distinct()
        )
        from django.contrib.auth import get_user_model
        User = get_user_model()
        for uid in user_ids:
            try:
                user = User.objects.get(pk=uid)
                add_suppression(user, email, reason)
            except User.DoesNotExist:
                pass

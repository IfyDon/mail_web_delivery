"""Fetch, parse, and route inbound mail delivered via SES receipt -> S3 -> SNS."""
import email
import logging
from email.message import Message as EmailMessage
from email.utils import parseaddr

from django.conf import settings
from django.db.models import Q

logger = logging.getLogger(__name__)


def fetch_raw_email(bucket: str, key: str) -> bytes:
    """Download the raw MIME message SES stored in S3."""
    import boto3

    s3 = boto3.client("s3", region_name=getattr(settings, "AWS_SES_REGION", None))
    obj = s3.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read()


def _decode_part(part: EmailMessage) -> str:
    payload = part.get_payload(decode=True) or b""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except (LookupError, TypeError):
        return payload.decode("utf-8", errors="replace")


def parse_raw_email(raw: bytes) -> dict:
    """Extract from/subject/text/html/attachments/headers from a raw MIME message."""
    msg: EmailMessage = email.message_from_bytes(raw)

    headers = {k: v for k, v in msg.items()}
    text_body = ""
    html_body = ""
    attachments = []

    if msg.is_multipart():
        for part in msg.walk():
            if part.is_multipart():
                continue

            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))
            filename = part.get_filename()

            is_attachment = "attachment" in disposition or (
                filename and content_type not in ("text/plain", "text/html")
            )
            if is_attachment:
                payload = part.get_payload(decode=True) or b""
                attachments.append({
                    "filename": filename or "attachment",
                    "content_type": content_type,
                    "content": payload,
                })
                continue

            if content_type == "text/plain" and not text_body:
                text_body = _decode_part(part)
            elif content_type == "text/html" and not html_body:
                html_body = _decode_part(part)
    else:
        if msg.get_content_type() == "text/html":
            html_body = _decode_part(msg)
        else:
            text_body = _decode_part(msg)

    return {
        "from_address": parseaddr(msg.get("From", ""))[1],
        "subject": msg.get("Subject", "") or "",
        "headers": headers,
        "text_body": text_body,
        "html_body": html_body,
        "attachments": attachments,
    }


def find_route(recipient: str):
    """Return the best-matching active InboundRoute for a recipient address, or None."""
    from apps.inbound.models import InboundRoute

    local_part, _, domain_part = recipient.lower().partition("@")
    routes = list(
        InboundRoute.objects
        .filter(domain__domain__iexact=domain_part, is_active=True)
        .filter(Q(local_part__iexact=local_part) | Q(match_type=InboundRoute.MATCH_WILDCARD))
        .select_related("domain", "user")
    )
    if not routes:
        return None
    # Prefer an exact-address match over a domain-wide wildcard.
    exact = [r for r in routes if r.match_type == InboundRoute.MATCH_EXACT]
    return exact[0] if exact else routes[0]


def route_inbound_email(*, ses_message_id: str, recipients: list, receipt: dict, parsed: dict) -> list:
    """Match each envelope recipient against InboundRoute rules, store the mail, and
    notify any subscribed webhooks. Returns the created InboundMessage instances."""
    from django.core.files.base import ContentFile

    from apps.inbound.models import InboundAttachment, InboundMessage
    from services.webhook_service import build_event_payload, trigger_webhooks

    spam_verdict = receipt.get("spamVerdict", {}).get("status", "")
    virus_verdict = receipt.get("virusVerdict", {}).get("status", "")

    created = []
    for recipient in recipients:
        recipient = recipient.lower().strip()
        if "@" not in recipient:
            continue

        route = find_route(recipient)

        if route is None:
            InboundMessage.objects.create(
                ses_message_id=ses_message_id,
                from_address=parsed["from_address"][:254],
                to_address=recipient,
                subject=parsed["subject"][:998],
                spam_verdict=spam_verdict,
                virus_verdict=virus_verdict,
                status=InboundMessage.STATUS_UNROUTED,
            )
            logger.info("inbound: no route matched %s (ses_message_id=%s)", recipient, ses_message_id)
            continue

        msg = InboundMessage.objects.create(
            user=route.user,
            route=route,
            ses_message_id=ses_message_id,
            from_address=parsed["from_address"][:254],
            to_address=recipient,
            subject=parsed["subject"][:998],
            text_body=parsed["text_body"],
            html_body=parsed["html_body"],
            headers=parsed["headers"],
            spam_verdict=spam_verdict,
            virus_verdict=virus_verdict,
            status=InboundMessage.STATUS_ROUTED,
        )

        for att in parsed["attachments"]:
            InboundAttachment.objects.create(
                message=msg,
                file=ContentFile(att["content"], name=att["filename"]),
                filename=att["filename"],
                content_type=att["content_type"] or "application/octet-stream",
                size=len(att["content"]),
            )

        payload = build_event_payload(
            "inbound",
            message_id=str(msg.pk),
            metadata={
                "from": msg.from_address,
                "to": msg.to_address,
                "subject": msg.subject,
                "route": route.address,
                "attachments": len(parsed["attachments"]),
            },
        )
        enqueued = trigger_webhooks(route.user, "inbound", payload)
        if enqueued:
            msg.status = InboundMessage.STATUS_FORWARDED
            msg.save(update_fields=["status"])

        created.append(msg)
        logger.info(
            "inbound: routed %s -> user=%s route=%s status=%s",
            recipient, route.user_id, route.pk, msg.status,
        )

    return created

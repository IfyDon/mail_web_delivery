"""POST /v1/send and POST /v1/send/batch — validate, suppress-check, queue, return 202."""
import logging

from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.serializers.message_serializers import SendEmailSerializer
from apps.domains.models import Domain
from apps.email_messages.models import Message
from services.billing_service import check_quota, increment_quota
from services.email_service import check_suppression, queue_email
from services.idempotency_service import (
    check_idempotency, get_idempotency_key, hash_request_body, store_idempotency,
)

logger = logging.getLogger(__name__)

_SEND_RESPONSE_EXAMPLE = OpenApiExample(
    "Queued",
    value={"message_id": "550e8400-e29b-41d4-a716-446655440000", "status": "queued", "submitted_at": "2025-01-15T10:30:00Z"},
    response_only=True,
    status_codes=["202"],
)

_IDEMPOTENCY_HEADER = OpenApiParameter(
    name="Idempotency-Key",
    location=OpenApiParameter.HEADER,
    required=False,
    type=str,
    description=(
        "Optional client-generated key. Replaying the same key within 24h "
        "returns the original response instead of sending a duplicate email. "
        "Reusing a key with a different request body returns 409."
    ),
)


def _resolve_domain(user, from_address: str):
    """Return the verified Domain matching the from_address, or None."""
    domain_part = from_address.split("@")[-1]
    return (
        Domain.objects.filter(user=user, domain=domain_part, verification_status="verified")
        .first()
    )


def _build_message(user, data: dict, domain) -> Message:
    template_id = data.get("template_id")
    template_version = None
    html_body = data.get("html_body", "")
    text_body = data.get("text_body", "")

    if template_id:
        from apps.email_templates.models import Template, TemplateVersion
        from services.template_service import render_template

        try:
            tmpl = Template.objects.get(pk=template_id, user=user)
            tv = TemplateVersion.objects.filter(template=tmpl, is_active=True).first()
            if tv:
                rendered = render_template(tv, context=data.get("template_data") or {})
                html_body = rendered.get("html", "")
                text_body = rendered.get("text", "")
                template_version = tv
        except Template.DoesNotExist:
            pass

    send_at = data.get("send_at")
    is_scheduled = send_at is not None

    return Message(
        user=user,
        domain=domain,
        template_version=template_version,
        to_address=data["to"],
        from_address=data["from_address"],
        reply_to=data.get("reply_to", ""),
        cc_addresses=data.get("cc", []),
        bcc_addresses=data.get("bcc", []),
        subject=data["subject"],
        html_body=html_body,
        text_body=text_body,
        stream=data.get("stream", Message.STREAM_TRANSACTIONAL),
        track_opens=data.get("track_opens", True),
        track_clicks=data.get("track_clicks", True),
        scheduled_at=send_at if is_scheduled else None,
        status=Message.STATUS_SCHEDULED if is_scheduled else Message.STATUS_QUEUED,
    )


def _save_attachments(msg: Message, attachments_data: list) -> None:
    """Decode base64 attachment payloads and store them against *msg*."""
    if not attachments_data:
        return

    import base64

    from django.core.files.base import ContentFile

    from apps.email_messages.models import MessageAttachment

    for att in attachments_data:
        raw = base64.b64decode(att["content"])
        MessageAttachment.objects.create(
            message=msg,
            file=ContentFile(raw, name=att["filename"]),
            filename=att["filename"],
            content_type=att.get("content_type", "application/octet-stream"),
            size=len(raw),
        )


@extend_schema(
    request=SendEmailSerializer,
    parameters=[_IDEMPOTENCY_HEADER],
    responses={202: {"type": "object", "properties": {
        "message_id": {"type": "string", "format": "uuid"},
        "status": {"type": "string"},
        "submitted_at": {"type": "string", "format": "date-time"},
    }}},
    examples=[_SEND_RESPONSE_EXAMPLE],
    summary="Send a single email",
    tags=["Sending"],
)
class SendView(APIView):
    def post(self, request):
        idem_key = get_idempotency_key(request)
        request_hash = hash_request_body(request.data) if idem_key else ""

        if idem_key:
            cached, conflict = check_idempotency(request.user, "send", idem_key, request_hash)
            if conflict:
                return Response(
                    {"status": "error", "code": 409, "message":
                     "Idempotency-Key was already used with a different request body."},
                    status=status.HTTP_409_CONFLICT,
                )
            if cached:
                return Response(cached["body"], status=cached["status"])

        status_code, body = self._handle(request)

        if idem_key:
            store_idempotency(request.user, "send", idem_key, request_hash, status_code, body)

        return Response(body, status=status_code)

    @staticmethod
    def _handle(request):
        serializer = SendEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        domain = _resolve_domain(request.user, data["from_address"])
        if domain is None:
            return status.HTTP_422_UNPROCESSABLE_ENTITY, {
                "status": "error", "code": 422, "errors": [
                    {"field": "from_address", "message": "Sender domain is not verified."}
                ],
            }

        if not check_quota(request.user):
            return status.HTTP_402_PAYMENT_REQUIRED, {
                "status": "error", "code": 402,
                "message": "Monthly email quota exceeded. Please upgrade your plan.",
            }

        if check_suppression(data["to"], user=request.user):
            return status.HTTP_202_ACCEPTED, {"message_id": None, "status": "suppressed"}

        msg = _build_message(request.user, data, domain)
        msg.save()
        _save_attachments(msg, data.get("attachments", []))
        if msg.status != Message.STATUS_SCHEDULED:
            queue_email(str(msg.pk))
        increment_quota(request.user)

        return status.HTTP_202_ACCEPTED, {
            "message_id": str(msg.pk), "status": msg.status,
            "submitted_at": msg.created_at.isoformat(),
        }


@extend_schema(
    request={"application/json": {"type": "object", "properties": {
        "messages": {"type": "array", "items": {"$ref": "#/components/schemas/SendEmail"}, "maxItems": 500}
    }}},
    parameters=[_IDEMPOTENCY_HEADER],
    responses={202: {"type": "object"}},
    summary="Send up to 500 emails in a batch",
    tags=["Sending"],
)
class BatchSendView(APIView):
    def post(self, request):
        idem_key = get_idempotency_key(request)
        request_hash = hash_request_body(request.data) if idem_key else ""

        if idem_key:
            cached, conflict = check_idempotency(request.user, "send_batch", idem_key, request_hash)
            if conflict:
                return Response(
                    {"status": "error", "code": 409, "message":
                     "Idempotency-Key was already used with a different request body."},
                    status=status.HTTP_409_CONFLICT,
                )
            if cached:
                return Response(cached["body"], status=cached["status"])

        status_code, body = self._handle(request)

        if idem_key:
            store_idempotency(request.user, "send_batch", idem_key, request_hash, status_code, body)

        return Response(body, status=status_code)

    @staticmethod
    def _handle(request):
        raw_messages = request.data.get("messages", [])
        if not isinstance(raw_messages, list) or len(raw_messages) == 0:
            return status.HTTP_400_BAD_REQUEST, {
                "status": "error", "code": 400, "errors": [
                    {"field": "messages", "message": "Provide a non-empty list of messages (max 500)."}
                ],
            }
        if len(raw_messages) > 500:
            return status.HTTP_400_BAD_REQUEST, {
                "status": "error", "code": 400, "errors": [
                    {"field": "messages", "message": "Batch size exceeds 500."}
                ],
            }

        if not check_quota(request.user):
            return status.HTTP_402_PAYMENT_REQUIRED, {
                "status": "error", "code": 402,
                "message": "Monthly email quota exceeded. Please upgrade your plan.",
            }

        results = []
        to_queue = []

        for idx, item in enumerate(raw_messages):
            serializer = SendEmailSerializer(data=item)
            if not serializer.is_valid():
                results.append({
                    "index": idx, "status": "validation_error", "errors": serializer.errors,
                })
                continue

            data = serializer.validated_data
            domain = _resolve_domain(request.user, data["from_address"])
            if domain is None:
                results.append({
                    "index": idx, "status": "error",
                    "message": "Sender domain not verified.",
                })
                continue

            if check_suppression(data["to"], user=request.user):
                results.append({"index": idx, "status": "suppressed", "message_id": None})
                continue

            msg = _build_message(request.user, data, domain)
            msg.save()
            _save_attachments(msg, data.get("attachments", []))
            to_queue.append(msg)
            results.append({"index": idx, "status": "queued", "message_id": str(msg.pk)})

        for msg in to_queue:
            queue_email(str(msg.pk))
            increment_quota(request.user)

        return status.HTTP_202_ACCEPTED, {"results": results, "total": len(results)}

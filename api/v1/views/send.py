"""POST /v1/send and POST /v1/send/batch — validate, suppress-check, queue, return 202."""
import logging

from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.serializers.message_serializers import SendEmailSerializer
from apps.domains.models import Domain
from apps.email_messages.models import Message
from services.billing_service import check_quota, increment_quota
from services.email_service import check_suppression, queue_email

logger = logging.getLogger(__name__)

_SEND_RESPONSE_EXAMPLE = OpenApiExample(
    "Queued",
    value={"message_id": "550e8400-e29b-41d4-a716-446655440000", "status": "queued", "submitted_at": "2025-01-15T10:30:00Z"},
    response_only=True,
    status_codes=["202"],
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
        subject=data["subject"],
        html_body=html_body,
        text_body=text_body,
        stream=data.get("stream", Message.STREAM_TRANSACTIONAL),
        track_opens=data.get("track_opens", True),
        track_clicks=data.get("track_clicks", True),
        scheduled_at=send_at if is_scheduled else None,
        status=Message.STATUS_SCHEDULED if is_scheduled else Message.STATUS_QUEUED,
    )


@extend_schema(
    request=SendEmailSerializer,
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
        serializer = SendEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        domain = _resolve_domain(request.user, data["from_address"])
        if domain is None:
            return Response(
                {"status": "error", "code": 422, "errors": [
                    {"field": "from_address", "message": "Sender domain is not verified."}
                ]},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        if not check_quota(request.user):
            return Response(
                {"status": "error", "code": 402,
                 "message": "Monthly email quota exceeded. Please upgrade your plan."},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        if check_suppression(data["to"]):
            return Response(
                {"message_id": None, "status": "suppressed"},
                status=status.HTTP_202_ACCEPTED,
            )

        msg = _build_message(request.user, data, domain)
        msg.save()
        if msg.status != Message.STATUS_SCHEDULED:
            queue_email(str(msg.pk))
        increment_quota(request.user)

        return Response(
            {"message_id": str(msg.pk), "status": msg.status, "submitted_at": msg.created_at},
            status=status.HTTP_202_ACCEPTED,
        )


@extend_schema(
    request={"application/json": {"type": "object", "properties": {
        "messages": {"type": "array", "items": {"$ref": "#/components/schemas/SendEmail"}, "maxItems": 500}
    }}},
    responses={202: {"type": "object"}},
    summary="Send up to 500 emails in a batch",
    tags=["Sending"],
)
class BatchSendView(APIView):
    def post(self, request):
        raw_messages = request.data.get("messages", [])
        if not isinstance(raw_messages, list) or len(raw_messages) == 0:
            return Response(
                {"status": "error", "code": 400, "errors": [
                    {"field": "messages", "message": "Provide a non-empty list of messages (max 500)."}
                ]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(raw_messages) > 500:
            return Response(
                {"status": "error", "code": 400, "errors": [
                    {"field": "messages", "message": "Batch size exceeds 500."}
                ]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not check_quota(request.user):
            return Response(
                {"status": "error", "code": 402,
                 "message": "Monthly email quota exceeded. Please upgrade your plan."},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

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

            if check_suppression(data["to"]):
                results.append({"index": idx, "status": "suppressed", "message_id": None})
                continue

            msg = _build_message(request.user, data, domain)
            msg.save()
            to_queue.append(msg)
            results.append({"index": idx, "status": "queued", "message_id": str(msg.pk)})

        for msg in to_queue:
            queue_email(str(msg.pk))
            increment_quota(request.user)

        return Response(
            {"results": results, "total": len(results)},
            status=status.HTTP_202_ACCEPTED,
        )

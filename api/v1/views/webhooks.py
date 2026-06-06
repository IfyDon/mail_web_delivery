"""Webhook management: CRUD + test + logs + retry endpoints."""
import logging

from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.webhooks.models import Webhook, WebhookDispatchLog
from services.webhook_service import build_event_payload, trigger_webhooks
from workers.tasks.webhook_dispatch import dispatch_webhook_task

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

class WebhookSerializer(serializers.ModelSerializer):
    secret = serializers.CharField(read_only=True)

    class Meta:
        model = Webhook
        fields = ["id", "url", "secret", "event_types", "is_active", "created_at"]
        read_only_fields = ["id", "secret", "created_at"]

    def validate_event_types(self, value):
        invalid = set(value) - set(Webhook.ALL_EVENT_TYPES)
        if invalid:
            raise serializers.ValidationError(
                f"Unknown event types: {sorted(invalid)}. "
                f"Valid types: {Webhook.ALL_EVENT_TYPES}"
            )
        return value


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

@extend_schema(tags=["Webhooks"])
class WebhookListView(APIView):
    @extend_schema(
        responses={200: WebhookSerializer(many=True)},
        summary="List webhooks",
    )
    def get(self, request):
        webhooks = Webhook.objects.filter(user=request.user)
        return Response(WebhookSerializer(webhooks, many=True).data)

    @extend_schema(
        request=WebhookSerializer,
        responses={201: WebhookSerializer},
        summary="Create a webhook",
    )
    def post(self, request):
        serializer = WebhookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        webhook = serializer.save(user=request.user)
        # Return the secret only on creation (shown once)
        data = WebhookSerializer(webhook).data
        data["secret"] = webhook.secret
        return Response(data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Webhooks"])
class WebhookDetailView(APIView):
    def _get_webhook(self, request, pk):
        try:
            return Webhook.objects.get(pk=pk, user=request.user)
        except Webhook.DoesNotExist:
            return None

    @extend_schema(
        responses={200: WebhookSerializer},
        summary="Retrieve a webhook",
    )
    def get(self, request, pk):
        webhook = self._get_webhook(request, pk)
        if webhook is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(WebhookSerializer(webhook).data)

    @extend_schema(
        request=WebhookSerializer,
        responses={200: WebhookSerializer},
        summary="Update a webhook",
    )
    def patch(self, request, pk):
        webhook = self._get_webhook(request, pk)
        if webhook is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = WebhookSerializer(webhook, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(
        responses={204: None},
        summary="Delete a webhook",
    )
    def delete(self, request, pk):
        webhook = self._get_webhook(request, pk)
        if webhook is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        webhook.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    request=None,
    responses={200: {"type": "object", "properties": {
        "enqueued": {"type": "integer"},
        "event_type": {"type": "string"},
    }}},
    summary="Send a test event to the webhook",
    tags=["Webhooks"],
)
class WebhookTestView(APIView):
    def post(self, request, pk):
        try:
            webhook = Webhook.objects.get(pk=pk, user=request.user)
        except Webhook.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if not webhook.is_active:
            return Response(
                {"detail": "Webhook is inactive."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        event_type = (webhook.event_types or [Webhook.EVENT_DELIVERED])[0]
        payload = build_event_payload(
            event_type,
            message_id="00000000-0000-0000-0000-000000000000",
            metadata={"test": True},
        )

        enqueued = trigger_webhooks(request.user, event_type, payload)
        return Response({"enqueued": enqueued, "event_type": event_type})


# ---------------------------------------------------------------------------
# Dispatch log serializer
# ---------------------------------------------------------------------------

class WebhookDispatchLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookDispatchLog
        fields = [
            "id", "event_type", "response_status", "response_body",
            "attempts", "succeeded", "created_at", "last_attempted_at",
        ]


# ---------------------------------------------------------------------------
# Logs view: GET /api/v1/webhooks/{id}/logs/
# ---------------------------------------------------------------------------

@extend_schema(
    responses={200: WebhookDispatchLogSerializer(many=True)},
    summary="Last 20 dispatch log entries for a webhook",
    tags=["Webhooks"],
)
class WebhookLogsView(APIView):
    def get(self, request, pk):
        try:
            webhook = Webhook.objects.get(pk=pk, user=request.user)
        except Webhook.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        logs = (
            WebhookDispatchLog.objects
            .filter(webhook=webhook)
            .order_by("-created_at")[:20]
        )
        return Response(WebhookDispatchLogSerializer(logs, many=True).data)


# ---------------------------------------------------------------------------
# Retry view: POST /api/v1/webhooks/{id}/retry/
# ---------------------------------------------------------------------------

@extend_schema(
    request=None,
    responses={202: {"type": "object", "properties": {"enqueued": {"type": "boolean"}}}},
    summary="Re-enqueue the most recent failed dispatch for a webhook",
    tags=["Webhooks"],
)
class WebhookRetryView(APIView):
    def post(self, request, pk):
        try:
            webhook = Webhook.objects.get(pk=pk, user=request.user)
        except Webhook.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        last_failed = (
            WebhookDispatchLog.objects
            .filter(webhook=webhook, succeeded=False)
            .order_by("-created_at")
            .first()
        )
        if last_failed is None:
            return Response(
                {"detail": "No failed dispatches to retry."},
                status=status.HTTP_404_NOT_FOUND,
            )

        dispatch_webhook_task.delay(webhook.id, last_failed.payload)
        return Response({"enqueued": True}, status=status.HTTP_202_ACCEPTED)

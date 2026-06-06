"""GET /v1/messages, GET /v1/messages/{id}, POST /v1/messages/{id}/resend."""
import logging

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.serializers.message_serializers import (
    MessageDetailSerializer,
    MessageListSerializer,
)
from apps.email_messages.models import Message
from services.email_service import queue_email

logger = logging.getLogger(__name__)

_STATUS_PARAM = OpenApiParameter(
    "status", str, description="Filter by message status", required=False
)
_DOMAIN_PARAM = OpenApiParameter(
    "domain", str, description="Filter by sender domain", required=False
)
_STREAM_PARAM = OpenApiParameter(
    "stream", str, description="Filter by stream (transactional/promotional)", required=False
)
_DATE_FROM_PARAM = OpenApiParameter(
    "date_from", str, description="ISO 8601 start date", required=False
)
_DATE_TO_PARAM = OpenApiParameter(
    "date_to", str, description="ISO 8601 end date", required=False
)


@extend_schema(
    parameters=[_STATUS_PARAM, _DOMAIN_PARAM, _STREAM_PARAM, _DATE_FROM_PARAM, _DATE_TO_PARAM],
    responses={200: MessageListSerializer(many=True)},
    summary="List messages",
    tags=["Messages"],
)
class MessageListView(ListAPIView):
    serializer_class = MessageListSerializer
    pagination_class = None  # uses DRF default (PAGE_SIZE=50 from settings)

    def get_queryset(self):
        qs = Message.objects.filter(user=self.request.user).select_related("domain")

        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        domain_filter = self.request.query_params.get("domain")
        if domain_filter:
            qs = qs.filter(domain__domain__iexact=domain_filter)

        stream_filter = self.request.query_params.get("stream")
        if stream_filter:
            qs = qs.filter(stream=stream_filter)

        date_from = self.request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(created_at__gte=date_from)

        date_to = self.request.query_params.get("date_to")
        if date_to:
            qs = qs.filter(created_at__lte=date_to)

        return qs


@extend_schema(
    responses={200: MessageDetailSerializer},
    summary="Retrieve a message with its event timeline",
    tags=["Messages"],
)
class MessageDetailView(RetrieveAPIView):
    serializer_class = MessageDetailSerializer

    def get_queryset(self):
        return (
            Message.objects
            .filter(user=self.request.user)
            .prefetch_related("events")
        )


@extend_schema(
    request=None,
    responses={202: {"type": "object"}},
    summary="Re-queue a permanently_failed message for delivery",
    tags=["Messages"],
)
class ResendMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            msg = Message.objects.get(pk=pk, user=request.user)
        except Message.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if msg.status != Message.STATUS_PERMANENTLY_FAILED:
            return Response(
                {"detail": "Only permanently_failed messages can be resent."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        msg.status = Message.STATUS_QUEUED
        msg.attempts = 0
        msg.save(update_fields=["status", "attempts"])

        queue_email(str(msg.id))

        return Response(
            {"message_id": str(msg.id), "status": msg.status},
            status=status.HTTP_202_ACCEPTED,
        )

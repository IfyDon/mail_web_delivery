"""CRUD for inbound routes + read-only access to received mail."""
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, viewsets
from rest_framework.generics import ListAPIView, RetrieveAPIView

from .models import InboundMessage, InboundRoute
from .serializers import (
    InboundMessageDetailSerializer,
    InboundMessageListSerializer,
    InboundRouteSerializer,
)


@extend_schema(tags=['Inbound'])
class InboundRouteViewSet(viewsets.ModelViewSet):
    serializer_class = InboundRouteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return InboundRoute.objects.filter(user=self.request.user).select_related('domain')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema(tags=['Inbound'])
class InboundMessageListView(ListAPIView):
    serializer_class = InboundMessageListSerializer

    def get_queryset(self):
        qs = InboundMessage.objects.filter(user=self.request.user).select_related('route', 'route__domain')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


@extend_schema(tags=['Inbound'])
class InboundMessageDetailView(RetrieveAPIView):
    serializer_class = InboundMessageDetailSerializer

    def get_queryset(self):
        return InboundMessage.objects.filter(user=self.request.user).prefetch_related('attachments')

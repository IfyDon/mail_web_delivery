"""CRUD views for per-user message streams."""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response

from .models import Stream
from .serializers import StreamSerializer


@extend_schema(tags=['Streams'])
class StreamListCreateView(ListCreateAPIView):
    serializer_class = StreamSerializer

    def get_queryset(self):
        return Stream.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema(tags=['Streams'])
class StreamDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = StreamSerializer
    lookup_field = 'slug'

    def get_queryset(self):
        return Stream.objects.filter(user=self.request.user)

    def destroy(self, request, *_args, **_kwargs):
        """Prevent deletion of built-in transactional/promotional streams."""
        instance = self.get_object()
        if instance.slug in (Stream.SLUG_TRANSACTIONAL, Stream.SLUG_PROMOTIONAL):
            return Response(
                {'detail': 'Built-in streams cannot be deleted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

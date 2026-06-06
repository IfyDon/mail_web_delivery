from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Template, TemplateVersion
from .serializers import (
    TemplateSerializer,
    TemplateVersionSerializer,
    TemplateRenderPreviewSerializer,
)
from services.template_service import render_template


class TemplateViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = TemplateSerializer

    def get_queryset(self):
        return Template.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["get", "post"], url_path="versions")
    def versions(self, request, pk=None):
        template = self.get_object()
        if request.method == "GET":
            qs = template.versions.all()
            serializer = TemplateVersionSerializer(qs, many=True)
            return Response(serializer.data)

        # POST -> create new version
        serializer = TemplateVersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        version = serializer.save(template=template, created_by=request.user)
        return Response(TemplateVersionSerializer(version).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="render_preview")
    def render_preview(self, request, pk=None):
        template = self.get_object()
        ser = TemplateRenderPreviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        context = data.get("context", {})
        compile_mjml = data.get("compile_mjml", False)

        # pick active version
        version = template.versions.filter(is_active=True).first()
        if not version:
            version = template.versions.first()
        if not version:
            return Response({"detail": "No template version available."}, status=400)

        rendered = render_template(version, context or {}, compile_mjml=compile_mjml)
        return Response(rendered)

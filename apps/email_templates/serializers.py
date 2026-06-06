from rest_framework import serializers

from .models import Template, TemplateVersion


class TemplateVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateVersion
        fields = (
            "id",
            "version",
            "html_content",
            "text_content",
            "mjml_source",
            "is_active",
            "created_at",
            "image",
        )


class TemplateSerializer(serializers.ModelSerializer):
    versions = TemplateVersionSerializer(many=True, read_only=True)

    class Meta:
        model = Template
        fields = ("id", "name", "slug", "description", "subject", "versions", "created_at", "updated_at")


class TemplateRenderPreviewSerializer(serializers.Serializer):
    context = serializers.DictField(child=serializers.CharField(), required=False)
    compile_mjml = serializers.BooleanField(default=False)


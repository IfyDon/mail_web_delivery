from django.utils.text import slugify
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
    versions  = TemplateVersionSerializer(many=True, read_only=True)
    slug      = serializers.SlugField(read_only=True)
    html_body = serializers.CharField(required=False, allow_blank=True, default="")
    text_body = serializers.CharField(required=False, allow_blank=True, default="")

    class Meta:
        model = Template
        fields = (
            "id", "name", "slug", "description", "subject",
            "html_body", "text_body",
            "versions", "created_at", "updated_at",
        )

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        v = instance.versions.filter(is_active=True).first() or instance.versions.first()
        rep["html_body"] = v.html_content if v else ""
        rep["text_body"] = v.text_content if v else ""
        return rep

    def _unique_slug(self, name, exclude_pk=None):
        base = slugify(name) or "template"
        slug, n = base, 1
        qs = Template.objects.filter(slug=slug)
        if exclude_pk:
            qs = qs.exclude(pk=exclude_pk)
        while qs.exists():
            slug = f"{base}-{n}"
            n += 1
            qs = Template.objects.filter(slug=slug)
            if exclude_pk:
                qs = qs.exclude(pk=exclude_pk)
        return slug

    def create(self, validated_data):
        html_body = validated_data.pop("html_body", "")
        text_body = validated_data.pop("text_body", "")
        validated_data["slug"] = self._unique_slug(validated_data.get("name", ""))
        template = Template.objects.create(**validated_data)
        TemplateVersion.objects.create(
            template=template,
            created_by=self.context["request"].user,
            html_content=html_body,
            text_content=text_body,
            is_active=True,
            version=1,
        )
        return template

    def update(self, instance, validated_data):
        html_body = validated_data.pop("html_body", None)
        text_body = validated_data.pop("text_body", None)
        if "name" in validated_data and validated_data["name"] != instance.name:
            validated_data["slug"] = self._unique_slug(validated_data["name"], exclude_pk=instance.pk)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if html_body is not None or text_body is not None:
            v = instance.versions.filter(is_active=True).first()
            if v:
                if html_body is not None:
                    v.html_content = html_body
                if text_body is not None:
                    v.text_content = text_body
                v.save(update_fields=["html_content", "text_content"])
            else:
                TemplateVersion.objects.create(
                    template=instance,
                    created_by=self.context["request"].user,
                    html_content=html_body or "",
                    text_content=text_body or "",
                    is_active=True,
                    version=1,
                )
        return instance


class TemplateRenderPreviewSerializer(serializers.Serializer):
    context = serializers.DictField(child=serializers.CharField(), required=False)
    compile_mjml = serializers.BooleanField(default=False)


from django.conf import settings
from django.db import models


class Template(models.Model):
    """Logical template container. Holds metadata and points to versions."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    description = models.TextField(blank=True)
    subject = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover - simple
        return f"{self.name}"


class TemplateVersion(models.Model):
    """A specific version of a template. Stores HTML/MJML and text variants."""

    template = models.ForeignKey(Template, related_name="versions", on_delete=models.CASCADE)
    version = models.PositiveIntegerField(default=1)
    html_content = models.TextField(blank=True)
    text_content = models.TextField(blank=True)
    mjml_source = models.TextField(blank=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    # Images and assets associated with this version. Storage backend may be S3.
    image = models.FileField(upload_to="templates/images/%Y/%m/%d", null=True, blank=True)

    class Meta:
        unique_together = ("template", "version")
        ordering = ("-version",)

    def __str__(self) -> str:  # pragma: no cover - simple
        return f"{self.template.name} v{self.version}"

    @property
    def rendered_html(self):
        return self.html_content or self.mjml_source

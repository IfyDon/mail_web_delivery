"""Server-rendered dashboard views for email template management."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.views import View

from apps.email_templates.models import Template, TemplateVersion


class TemplatesView(LoginRequiredMixin, View):
    login_url = "/login/"
    template_name = "dashboard/templates.html"

    def get(self, request):
        templates = Template.objects.filter(user=request.user)
        return render(request, self.template_name, {"templates": templates})


class TemplateCreateView(LoginRequiredMixin, View):
    login_url = "/login/"
    template_name = "dashboard/template_create.html"

    def get(self, request):
        return render(request, self.template_name, {})

    def post(self, request):
        name = request.POST.get("name", "").strip()
        subject = request.POST.get("subject", "").strip()
        description = request.POST.get("description", "").strip()
        html_content = request.POST.get("html_content", "")
        text_content = request.POST.get("text_content", "")

        if not name:
            messages.error(request, "Template name is required.")
            return render(request, self.template_name, {
                "name": name, "subject": subject, "description": description,
                "html_content": html_content, "text_content": text_content,
            })

        base_slug = slugify(name) or "template"
        slug = base_slug
        suffix = 1
        while Template.objects.filter(user=request.user, slug=slug).exists():
            suffix += 1
            slug = f"{base_slug}-{suffix}"

        template = Template.objects.create(
            user=request.user, name=name, slug=slug,
            description=description, subject=subject,
        )
        TemplateVersion.objects.create(
            template=template, version=1,
            html_content=html_content, text_content=text_content,
            is_active=True, created_by=request.user,
        )
        messages.success(request, f'Created template "{name}".')
        return redirect("templates")


class TemplateEditView(LoginRequiredMixin, View):
    login_url = "/login/"
    template_name = "dashboard/template_edit.html"

    def get(self, request, pk):
        template = get_object_or_404(Template, pk=pk, user=request.user)
        active_version = template.versions.filter(is_active=True).first() or template.versions.first()
        return render(request, self.template_name, {"tpl": template, "active_version": active_version})

    def post(self, request, pk):
        template = get_object_or_404(Template, pk=pk, user=request.user)
        template.name = request.POST.get("name", template.name).strip() or template.name
        template.subject = request.POST.get("subject", "").strip()
        template.description = request.POST.get("description", "").strip()
        template.save()

        html_content = request.POST.get("html_content", "")
        text_content = request.POST.get("text_content", "")

        next_version = (template.versions.aggregate(Max("version"))["version__max"] or 0) + 1
        template.versions.update(is_active=False)
        TemplateVersion.objects.create(
            template=template, version=next_version,
            html_content=html_content, text_content=text_content,
            is_active=True, created_by=request.user,
        )
        messages.success(request, f'Saved template "{template.name}" (v{next_version}).')
        return redirect("templates")


class TemplateDeleteView(LoginRequiredMixin, View):
    login_url = "/login/"

    def post(self, request, pk):
        template = get_object_or_404(Template, pk=pk, user=request.user)
        name = template.name
        template.delete()
        messages.success(request, f'Deleted template "{name}".')
        return redirect("templates")

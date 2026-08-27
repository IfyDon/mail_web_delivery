"""Server-rendered dashboard view for the (read-only) audit log."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.views.generic import TemplateView

from apps.accounts.models import AuditLog


class AuditLogView(LoginRequiredMixin, TemplateView):
    login_url = "/login/"
    template_name = "dashboard/audit_log.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = AuditLog.objects.filter(user=self.request.user)
        paginator = Paginator(qs, 50)
        page = paginator.get_page(self.request.GET.get("page"))
        ctx["page_obj"] = page
        return ctx

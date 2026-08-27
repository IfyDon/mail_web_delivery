"""Server-rendered dashboard view for the analytics overview."""
from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import TemplateView

from services.analytics_service import get_daily_stats, get_totals


class AnalyticsView(LoginRequiredMixin, TemplateView):
    login_url = "/login/"
    template_name = "dashboard/analytics.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        try:
            days = int(self.request.GET.get("days", 30))
        except ValueError:
            days = 30
        if days not in (7, 30, 90):
            days = 30

        date_to = timezone.now().date()
        date_from = date_to - timedelta(days=days - 1)

        stats = get_daily_stats(self.request.user, date_from, date_to)
        totals = get_totals(stats)

        ctx.update({
            "days": days,
            "stats": stats,
            "totals": totals,
        })
        return ctx

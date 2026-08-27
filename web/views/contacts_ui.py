"""Server-rendered dashboard view for per-contact engagement scoring."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg
from django.views.generic import TemplateView

from apps.analytics.models import ContactEngagement

_SEGMENTS = {
    "engaged": ("-score", {"score__gt": 0}),
    "at_risk": ("score", {"score__lt": 0}),
}


class ContactsView(LoginRequiredMixin, TemplateView):
    login_url = "/login/"
    template_name = "dashboard/contacts.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        segment = self.request.GET.get("segment", "")
        query = self.request.GET.get("q", "").strip()

        qs = ContactEngagement.objects.filter(user=self.request.user)
        if query:
            qs = qs.filter(email__icontains=query)

        if segment in _SEGMENTS:
            order, extra_filter = _SEGMENTS[segment]
            qs = qs.filter(**extra_filter).order_by(order)
        else:
            qs = qs.order_by("-score")

        all_contacts = ContactEngagement.objects.filter(user=self.request.user)
        stats = all_contacts.aggregate(avg_score=Avg("score"))

        ctx.update({
            "contacts": list(qs[:200]),
            "segment": segment,
            "query": query,
            "total_tracked": all_contacts.count(),
            "engaged_count": all_contacts.filter(score__gt=0).count(),
            "at_risk_count": all_contacts.filter(score__lt=0).count(),
            "avg_score": stats["avg_score"],
        })
        return ctx

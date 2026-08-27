"""Server-rendered dashboard view for billing/plan/invoices."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class BillingView(LoginRequiredMixin, TemplateView):
    login_url = "/login/"
    template_name = "dashboard/billing.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        subscription = None
        plan = None
        try:
            subscription = user.subscription
            plan = subscription.plan
        except Exception:
            pass

        quota = None
        usage_pct = 0
        try:
            quota = user.quota
            if quota.monthly_limit and quota.monthly_limit > 0:
                usage_pct = min(100, round(quota.emails_sent_this_month / quota.monthly_limit * 100))
        except Exception:
            pass

        invoices = []
        if subscription:
            invoices = subscription.invoices.all()[:50]

        ctx.update({
            "subscription": subscription,
            "plan": plan,
            "quota": quota,
            "usage_pct": usage_pct,
            "invoices": invoices,
        })
        return ctx

"""Server-rendered dashboard views for billing/plan/invoices."""
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views import View
from django.views.generic import TemplateView

from apps.billing.models import Plan
from services.billing_service import create_checkout_url


class BillingCheckoutView(LoginRequiredMixin, View):
    """Start a Paystack checkout for a plan and redirect straight to it.

    Triggered from the pricing page (authenticated users) or by SignUpView
    right after signup (when the visitor arrived via /pricing/?plan=...).
    """
    login_url = "/login/"

    def get(self, request):
        plan_slug = request.GET.get("plan", "").strip()
        if not plan_slug or plan_slug == "free":
            return redirect("billing")

        if not Plan.objects.filter(slug=plan_slug, is_active=True).exists():
            messages.error(request, f'Unknown plan "{plan_slug}".')
            return redirect("pricing")

        success_url = f"{settings.BASE_URL}/dashboard/billing/?checkout=success"
        cancel_url = f"{settings.BASE_URL}/pricing/?checkout=cancel"

        try:
            checkout_url = create_checkout_url(
                request.user, plan_slug=plan_slug,
                success_url=success_url, cancel_url=cancel_url,
            )
        except Exception as exc:
            messages.error(request, f"Couldn't start checkout: {exc}")
            return redirect("pricing")

        return redirect(checkout_url)


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

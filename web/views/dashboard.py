from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"
    login_url = "/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        # ── Plan & subscription ───────────────────────────────────────────
        subscription = None
        plan = None
        try:
            subscription = user.subscription
            plan = subscription.plan
        except Exception:
            pass

        # ── Usage quota ───────────────────────────────────────────────────
        quota = None
        usage_pct = 0
        try:
            quota = user.quota
            if quota.monthly_limit and quota.monthly_limit > 0:
                usage_pct = min(100, round(quota.emails_sent_this_month / quota.monthly_limit * 100))
        except Exception:
            pass

        # ── API Keys ──────────────────────────────────────────────────────
        api_keys = user.api_keys.filter(is_active=True).order_by('-created_at')

        # ── Quick counts ──────────────────────────────────────────────────
        domain_count = 0
        webhook_count = 0
        suppression_count = 0
        try:
            from apps.domains.models import Domain
            domain_count = Domain.objects.filter(user=user).count()
        except Exception:
            pass
        try:
            from apps.webhooks.models import Webhook
            webhook_count = Webhook.objects.filter(user=user, is_active=True).count()
        except Exception:
            pass
        try:
            from apps.suppressions.models import Suppression
            suppression_count = Suppression.objects.filter(user=user).count()
        except Exception:
            pass

        ctx.update({
            'subscription': subscription,
            'plan': plan,
            'quota': quota,
            'usage_pct': usage_pct,
            'api_keys': api_keys,
            'domain_count': domain_count,
            'webhook_count': webhook_count,
            'suppression_count': suppression_count,
            'checkout_status': self.request.GET.get('checkout', ''),
        })
        return ctx

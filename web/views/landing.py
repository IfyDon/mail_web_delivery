"""Marketing landing page views."""
from django.views.generic import TemplateView


class IndexView(TemplateView):
    template_name = "landing/index.html"


class FeaturesView(TemplateView):
    template_name = "landing/features.html"


class PricingView(TemplateView):
    template_name = "landing/pricing.html"


class EmailApiView(TemplateView):
    template_name = "landing/email_api.html"


# ── Individual feature pages ──────────────────────────────────────────

class FeatureTransactionalView(TemplateView):
    template_name = "landing/feature_transactional.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["items"] = [
            "Password resets and magic links",
            "Order confirmations and receipts",
            "Account alerts and security notifications",
            "Welcome emails and onboarding flows",
            "Invoice and billing notifications",
            "Two-factor authentication codes",
        ]
        ctx["cards"] = [
            {"title": "Dedicated IP pool", "body": "Transactional sends use a separate IP from promotional mail — one can never harm the other.", "icon": "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"},
            {"title": "Automatic retries", "body": "Failed sends are retried up to 5 times with exponential back-off before being permanently failed.", "icon": "M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"},
            {"title": "Event timeline", "body": "Every message has a full event log — queued, sending, delivered, opened, clicked, bounced.", "icon": "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"},
            {"title": "Open & click tracking", "body": "Pixel tracking and link rewriting give you opens and clicks without extra integration work.", "icon": "M15 12a3 3 0 11-6 0 3 3 0 016 0zM2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"},
            {"title": "Suppression guard", "body": "Hard bounces, complaints, and manual suppressions are checked before every send — automatically.", "icon": "M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"},
            {"title": "Webhooks on every event", "body": "POST real-time event notifications to your endpoint for delivered, opened, bounced, and more.", "icon": "M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"},
        ]
        return ctx


class FeatureDeliveryView(TemplateView):
    template_name = "landing/feature_delivery.html"


class FeatureTemplatesView(TemplateView):
    template_name = "landing/feature_templates.html"


class FeatureInboundView(TemplateView):
    template_name = "landing/feature_inbound.html"


class FeatureAnalyticsView(TemplateView):
    template_name = "landing/feature_analytics.html"


class FeatureIntegrationsView(TemplateView):
    template_name = "landing/feature_integrations.html"


class FeatureBulkApiView(TemplateView):
    template_name = "landing/feature_bulk_api.html"

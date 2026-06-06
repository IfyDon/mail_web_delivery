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

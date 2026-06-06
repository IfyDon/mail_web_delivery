"""Legal pages: Terms, Privacy Policy, GDPR/Cookie Policy."""
from django.views.generic import TemplateView


class TermsView(TemplateView):
    template_name = "legal/terms.html"


class PrivacyView(TemplateView):
    template_name = "legal/privacy.html"


class GDPRView(TemplateView):
    template_name = "legal/gdpr.html"

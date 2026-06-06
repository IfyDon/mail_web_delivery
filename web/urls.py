"""URL patterns for the marketing site and public-facing web views."""
from django.urls import path

from web.views.account import LoginView, LogoutView, SignUpView
from web.views.dashboard import DashboardView
from web.views.landing import EmailApiView, FeaturesView, IndexView, PricingView
from web.views.legal import GDPRView, PrivacyView, TermsView

urlpatterns = [
    # Landing pages
    path("", IndexView.as_view(), name="home"),
    path("features/", FeaturesView.as_view(), name="features"),
    path("pricing/", PricingView.as_view(), name="pricing"),

    # Auth
    path("signup/", SignUpView.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),

    # Dashboard (authenticated)
    path("dashboard/", DashboardView.as_view(), name="dashboard"),

    # Legal pages
    path("terms/", TermsView.as_view(), name="terms"),
    path("privacy/", PrivacyView.as_view(), name="privacy"),
    path("gdpr/", GDPRView.as_view(), name="gdpr"),
]

"""URL patterns for the marketing site and public-facing web views."""
from django.contrib.auth import views as auth_views
from django.urls import path

from web.forms.auth_forms import StyledSetPasswordForm
from web.views.account import LoginView, LogoutView, SignUpView
from web.views.dashboard import DashboardView
from web.views.landing import (
    EmailApiView, FeaturesView, IndexView, PricingView,
    FeatureTransactionalView, FeatureDeliveryView, FeatureTemplatesView,
    FeatureInboundView, FeatureAnalyticsView, FeatureIntegrationsView,
    FeatureBulkApiView,
)
from web.views.legal import GDPRView, PrivacyView, TermsView

urlpatterns = [
    # Landing pages
    path("", IndexView.as_view(), name="home"),
    path("features/", FeaturesView.as_view(), name="features"),
    path("features/transactional-email/", FeatureTransactionalView.as_view(), name="feature_transactional"),
    path("features/email-delivery/", FeatureDeliveryView.as_view(), name="feature_delivery"),
    path("features/email-templates/", FeatureTemplatesView.as_view(), name="feature_templates"),
    path("features/inbound-email/", FeatureInboundView.as_view(), name="feature_inbound"),
    path("features/analytics-retention/", FeatureAnalyticsView.as_view(), name="feature_analytics"),
    path("features/integrations/", FeatureIntegrationsView.as_view(), name="feature_integrations"),
    path("features/bulk-api/", FeatureBulkApiView.as_view(), name="feature_bulk_api"),
    path("email-api/", EmailApiView.as_view(), name="email_api"),
    path("pricing/", PricingView.as_view(), name="pricing"),

    # Auth
    path("signup/", SignUpView.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),

    # Password reset flow
    path("password-reset/",
         auth_views.PasswordResetView.as_view(
             template_name="registration/password_reset_form.html",
             email_template_name="registration/password_reset_email.html",
             subject_template_name="registration/password_reset_subject.txt",
             success_url="/password-reset/done/",
         ),
         name="password_reset"),
    path("password-reset/done/",
         auth_views.PasswordResetDoneView.as_view(
             template_name="registration/password_reset_done.html",
         ),
         name="password_reset_done"),
    path("password-reset/<uidb64>/<token>/",
         auth_views.PasswordResetConfirmView.as_view(
             template_name="registration/password_reset_confirm.html",
             form_class=StyledSetPasswordForm,
             success_url="/password-reset/complete/",
         ),
         name="password_reset_confirm"),
    path("password-reset/complete/",
         auth_views.PasswordResetCompleteView.as_view(
             template_name="registration/password_reset_complete.html",
         ),
         name="password_reset_complete"),

    # Dashboard (authenticated)
    path("dashboard/", DashboardView.as_view(), name="dashboard"),

    # Legal pages
    path("terms/", TermsView.as_view(), name="terms"),
    path("privacy/", PrivacyView.as_view(), name="privacy"),
    path("gdpr/", GDPRView.as_view(), name="gdpr"),
]

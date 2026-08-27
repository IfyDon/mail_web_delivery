"""URL patterns for the marketing site and public-facing web views."""
from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import TemplateView

from web.forms.auth_forms import StyledSetPasswordForm
from web.views.account import LoginView, LogoutView, SignUpView, TwoFactorVerifyView
from web.views.analytics_ui import AnalyticsView
from web.views.api_keys import APIKeyCreateView, APIKeyRevokeView
from web.views.audit_ui import AuditLogView
from web.views.billing_ui import BillingCheckoutView, BillingView
from web.views.dashboard import DashboardView
from web.views.domains_ui import DomainDeleteView, DomainVerifyView, DomainsView
from web.views.inbound_ui import (
    InboundMessageDetailView, InboundRouteDeleteView, InboundView,
)
from web.views.messages_ui import MessageDetailView, MessageResendView, MessagesView
from web.views.settings_ui import (
    AccountDeleteView, DataExportDownloadView, DataExportRequestView, PasswordChangeView,
    SettingsView, TwoFactorConfirmView, TwoFactorDisableView, TwoFactorSetupView,
)
from web.views.streams_ui import StreamArchiveView, StreamDeleteView, StreamsView
from web.views.suppressions_ui import SuppressionRemoveView, SuppressionsView
from web.views.team_ui import (
    AcceptInviteView, TeamRemoveView, TeamResendView, TeamRoleChangeView, TeamView,
)
from web.views.templates_ui import (
    TemplateCreateView, TemplateDeleteView, TemplateEditView, TemplatesView,
)
from web.views.webhooks_ui import WebhookDeleteView, WebhooksView
from web.views.landing import (
    EmailApiView, FeaturesView, IndexView, PricingView,
    FeatureTransactionalView, FeatureDeliveryView, FeatureTemplatesView,
    FeatureInboundView, FeatureAnalyticsView, FeatureIntegrationsView,
    FeatureBulkApiView,
)
from web.views.legal import GDPRView, PrivacyView, TermsView

urlpatterns = [
    # SEO
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
        name="robots",
    ),
    path(
        "sitemap.xml",
        TemplateView.as_view(template_name="sitemap.xml", content_type="application/xml"),
        name="sitemap",
    ),

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
    path("login/2fa/", TwoFactorVerifyView.as_view(), name="two_factor_verify"),
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
    path("dashboard/api-keys/create/", APIKeyCreateView.as_view(), name="api_key_create"),
    path("dashboard/api-keys/<int:pk>/revoke/", APIKeyRevokeView.as_view(), name="api_key_revoke"),

    path("dashboard/domains/", DomainsView.as_view(), name="domains"),
    path("dashboard/domains/<int:pk>/verify/", DomainVerifyView.as_view(), name="domain_verify"),
    path("dashboard/domains/<int:pk>/delete/", DomainDeleteView.as_view(), name="domain_delete"),

    path("dashboard/templates/", TemplatesView.as_view(), name="templates"),
    path("dashboard/templates/create/", TemplateCreateView.as_view(), name="template_create"),
    path("dashboard/templates/<int:pk>/edit/", TemplateEditView.as_view(), name="template_edit"),
    path("dashboard/templates/<int:pk>/delete/", TemplateDeleteView.as_view(), name="template_delete"),

    path("dashboard/webhooks/", WebhooksView.as_view(), name="webhooks"),
    path("dashboard/webhooks/<int:pk>/delete/", WebhookDeleteView.as_view(), name="webhook_delete"),

    path("dashboard/inbound/", InboundView.as_view(), name="inbound"),
    path("dashboard/inbound/<int:pk>/delete/", InboundRouteDeleteView.as_view(), name="inbound_route_delete"),
    path("dashboard/inbound/messages/<int:pk>/", InboundMessageDetailView.as_view(), name="inbound_message_detail"),

    path("dashboard/suppressions/", SuppressionsView.as_view(), name="suppressions"),
    path("dashboard/suppressions/<int:pk>/remove/", SuppressionRemoveView.as_view(), name="suppression_remove"),

    path("dashboard/messages/", MessagesView.as_view(), name="messages"),
    path("dashboard/messages/<uuid:pk>/", MessageDetailView.as_view(), name="message_detail"),
    path("dashboard/messages/<uuid:pk>/resend/", MessageResendView.as_view(), name="message_resend"),
    path("dashboard/analytics/", AnalyticsView.as_view(), name="analytics"),
    path("dashboard/billing/", BillingView.as_view(), name="billing"),
    path("dashboard/billing/checkout/", BillingCheckoutView.as_view(), name="billing_checkout"),

    path("dashboard/team/", TeamView.as_view(), name="team"),
    path("dashboard/team/<int:pk>/role/", TeamRoleChangeView.as_view(), name="team_role_change"),
    path("dashboard/team/<int:pk>/resend/", TeamResendView.as_view(), name="team_resend"),
    path("dashboard/team/<int:pk>/remove/", TeamRemoveView.as_view(), name="team_remove"),
    path("accept-invite/<str:token>/", AcceptInviteView.as_view(), name="accept_invite"),

    path("dashboard/streams/", StreamsView.as_view(), name="streams"),
    path("dashboard/streams/<int:pk>/archive/", StreamArchiveView.as_view(), name="stream_archive"),
    path("dashboard/streams/<int:pk>/delete/", StreamDeleteView.as_view(), name="stream_delete"),

    path("dashboard/settings/", SettingsView.as_view(), name="settings"),
    path("dashboard/settings/password/", PasswordChangeView.as_view(), name="password_change"),
    path("dashboard/settings/2fa/setup/", TwoFactorSetupView.as_view(), name="2fa_setup"),
    path("dashboard/settings/2fa/confirm/", TwoFactorConfirmView.as_view(), name="2fa_confirm"),
    path("dashboard/settings/2fa/disable/", TwoFactorDisableView.as_view(), name="2fa_disable"),
    path("dashboard/settings/export/", DataExportRequestView.as_view(), name="data_export_request"),
    path("dashboard/settings/export/<int:pk>/download/", DataExportDownloadView.as_view(), name="data_export_download"),
    path("dashboard/settings/delete-account/", AccountDeleteView.as_view(), name="account_delete"),

    path("dashboard/audit-log/", AuditLogView.as_view(), name="audit_log"),

    # Legal pages
    path("terms/", TermsView.as_view(), name="terms"),
    path("privacy/", PrivacyView.as_view(), name="privacy"),
    path("gdpr/", GDPRView.as_view(), name="gdpr"),
]

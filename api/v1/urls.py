"""URL routing for API v1."""
from django.urls import include, path

from api.v1.views.messages import MessageDetailView, MessageListView, ResendMessageView
from api.v1.views.send import BatchSendView, SendView
from api.v1.views.ses_inbound import SESInboundView
from api.v1.views.billing import (
    BillingOverviewView,
    CheckoutSessionView,
    InvoiceListView,
    PortalSessionView,
)
from api.v1.views.stats import StatsView
from api.v1.views.stats_export import StatsExportView
from api.v1.views.stripe_webhook import StripeWebhookView
from api.v1.views.suppressions import SuppressionDetailView, SuppressionListView
from api.v1.views.team import TeamDetailView, TeamListView
from api.v1.views.webhooks import (
    WebhookDetailView,
    WebhookListView,
    WebhookLogsView,
    WebhookRetryView,
    WebhookTestView,
)

urlpatterns = [
    # Auth & account management
    path("auth/", include("apps.authentication.urls")),
    path("accounts/", include("apps.accounts.urls")),

    # Domain management
    path("domains/", include("apps.domains.urls")),

    # Message streams
    path("streams/", include("apps.streams.urls")),

    # Email templates
    path("templates/", include("apps.email_templates.urls")),

    # Sending
    path("send", SendView.as_view(), name="send"),
    path("send/batch", BatchSendView.as_view(), name="send-batch"),

    # Message history
    path("messages/", MessageListView.as_view(), name="message-list"),
    path("messages/<uuid:pk>/", MessageDetailView.as_view(), name="message-detail"),
    path("messages/<uuid:pk>/resend/", ResendMessageView.as_view(), name="message-resend"),

    # Analytics
    path("stats/", StatsView.as_view(), name="stats"),
    path("stats/export/", StatsExportView.as_view(), name="stats-export"),

    # Webhooks (order: specific paths before generic <pk>/)
    path("webhooks/ses/", SESInboundView.as_view(), name="ses-inbound"),
    path("webhooks/stripe/", StripeWebhookView.as_view(), name="stripe-webhook"),
    path("webhooks/", WebhookListView.as_view(), name="webhook-list"),
    path("webhooks/<int:pk>/", WebhookDetailView.as_view(), name="webhook-detail"),
    path("webhooks/<int:pk>/test/", WebhookTestView.as_view(), name="webhook-test"),
    path("webhooks/<int:pk>/logs/", WebhookLogsView.as_view(), name="webhook-logs"),
    path("webhooks/<int:pk>/retry/", WebhookRetryView.as_view(), name="webhook-retry"),

    # Suppression list
    path("suppressions/", SuppressionListView.as_view(), name="suppression-list"),
    path("suppressions/<str:email>/", SuppressionDetailView.as_view(), name="suppression-detail"),

    # Team management
    path("team/", TeamListView.as_view(), name="team-list"),
    path("team/<int:pk>/", TeamDetailView.as_view(), name="team-detail"),

    # Billing
    path("billing/", BillingOverviewView.as_view(), name="billing-overview"),
    path("billing/checkout/", CheckoutSessionView.as_view(), name="billing-checkout"),
    path("billing/portal/", PortalSessionView.as_view(), name="billing-portal"),
    path("billing/invoices/", InvoiceListView.as_view(), name="billing-invoices"),
]

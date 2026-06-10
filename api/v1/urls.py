"""URL routing for API v1."""
from django.urls import include, path
from rest_framework.decorators import api_view
from rest_framework.response import Response

from api.v1.views.messages import MessageDetailView, MessageListView, ResendMessageView
from api.v1.views.schedule import CancelScheduleView
from api.v1.views.send import BatchSendView, SendView
from api.v1.views.ses_inbound import SESInboundView
from api.v1.views.contacts import ContactEngagementView
from api.v1.views.message_stream import message_stream_view
from api.v1.views.billing import (
    BillingOverviewView,
    CheckoutSessionView,
    InvoiceListView,
    PortalSessionView,
)
from api.v1.views.stats import StatsView
from api.v1.views.stats_export import StatsExportView
from api.v1.views.stripe_webhook import StripeWebhookView
from api.v1.views.suppressions import (
    SuppressionDetailView,
    SuppressionExportView,
    SuppressionListView,
)
from api.v1.views.team import TeamDetailView, TeamListView
from api.v1.views.webhooks import (
    WebhookDetailView,
    WebhookListView,
    WebhookLogsView,
    WebhookRetryView,
    WebhookTestView,
)

@api_view(['GET'])
def api_root(request):
    """API v1 root endpoint."""
    return Response({
        'status': 'ok',
        'version': 'v1',
        'message': 'Web Mail API v1',
        'endpoints': {
            'auth': request.build_absolute_uri('/api/v1/auth/'),
            'accounts': request.build_absolute_uri('/api/v1/accounts/'),
            'domains': request.build_absolute_uri('/api/v1/domains/'),
            'messages': request.build_absolute_uri('/api/v1/messages/'),
            'send': request.build_absolute_uri('/api/v1/send/'),
            'stats': request.build_absolute_uri('/api/v1/stats/'),
            'webhooks': request.build_absolute_uri('/api/v1/webhooks/'),
            'billing': request.build_absolute_uri('/api/v1/billing/'),
        }
    })

urlpatterns = [
    # Root endpoint
    path("", api_root, name="api-root"),

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
    path("messages/stream/", message_stream_view, name="message-stream"),
    path("messages/", MessageListView.as_view(), name="message-list"),
    path("messages/<uuid:pk>/", MessageDetailView.as_view(), name="message-detail"),
    path("messages/<uuid:pk>/resend/", ResendMessageView.as_view(), name="message-resend"),
    path(
        "messages/<uuid:pk>/schedule/",
        CancelScheduleView.as_view(),
        name="message-cancel-schedule",
    ),

    # Analytics
    path("stats/", StatsView.as_view(), name="stats"),
    path("stats/export/", StatsExportView.as_view(), name="stats-export"),

    # Contacts / engagement
    path("contacts/engagement/", ContactEngagementView.as_view(), name="contact-engagement"),

    # Webhooks (order: specific paths before generic <pk>/)
    path("webhooks/ses/", SESInboundView.as_view(), name="ses-inbound"),
    path("webhooks/stripe/", StripeWebhookView.as_view(), name="stripe-webhook"),
    path("webhooks/", WebhookListView.as_view(), name="webhook-list"),
    path("webhooks/<int:pk>/", WebhookDetailView.as_view(), name="webhook-detail"),
    path("webhooks/<int:pk>/test/", WebhookTestView.as_view(), name="webhook-test"),
    path("webhooks/<int:pk>/logs/", WebhookLogsView.as_view(), name="webhook-logs"),
    path("webhooks/<int:pk>/retry/", WebhookRetryView.as_view(), name="webhook-retry"),

    # Suppression list (export before list so the literal path wins)
    path("suppressions/export/", SuppressionExportView.as_view(), name="suppression-export"),
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

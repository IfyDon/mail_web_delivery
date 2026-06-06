"""Inbound Stripe webhook receiver — verifies signature and dispatches events."""
import logging
import os

from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from services.billing_service import sync_from_stripe_subscription, sync_invoice

logger = logging.getLogger(__name__)

# Events we handle; all others are acknowledged but ignored.
_HANDLED_EVENTS = {
    'checkout.session.completed',
    'customer.subscription.updated',
    'customer.subscription.deleted',
    'invoice.paid',
    'invoice.payment_failed',
}


@extend_schema(exclude=True)
class StripeWebhookView(APIView):
    """Stripe sends POST requests here for every subscribed event."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @csrf_exempt
    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
        secret = os.getenv('STRIPE_WEBHOOK_SECRET', '')

        if not secret:
            logger.error('StripeWebhookView: STRIPE_WEBHOOK_SECRET not configured')
            return Response({'detail': 'Webhook secret not configured.'}, status=500)

        try:
            from integrations.stripe.client import StripeClient
            event = StripeClient().construct_event(payload, sig_header, secret)
        except ValueError:
            logger.warning('StripeWebhookView: invalid payload')
            return Response({'detail': 'Invalid payload.'}, status=400)
        except Exception as exc:  # noqa: BLE001
            logger.warning('StripeWebhookView: signature verification failed — %s', exc)
            return Response({'detail': 'Signature verification failed.'}, status=400)

        event_type = event['type']
        if event_type not in _HANDLED_EVENTS:
            return Response({'received': True})

        try:
            _dispatch(event_type, event['data']['object'])
        except Exception as exc:  # noqa: BLE001
            logger.exception('StripeWebhookView: error handling %s — %s', event_type, exc)
            # Return 200 so Stripe does not retry on application errors.

        return Response({'received': True})


def _dispatch(event_type: str, obj: dict) -> None:
    """Route a Stripe event object to the appropriate handler."""
    if event_type == 'checkout.session.completed':
        _handle_checkout_completed(obj)
    elif event_type in ('customer.subscription.updated', 'customer.subscription.deleted'):
        sync_from_stripe_subscription(obj)
    elif event_type in ('invoice.paid', 'invoice.payment_failed'):
        sync_invoice(obj)
        if event_type == 'invoice.paid':
            _reset_quota_for_invoice(obj)


def _handle_checkout_completed(session: dict) -> None:
    """Sync the subscription created by a completed Checkout session."""
    subscription_id = session.get('subscription')
    if not subscription_id:
        return
    from integrations.stripe.client import StripeClient
    stripe_sub = StripeClient().retrieve_subscription(subscription_id)
    sync_from_stripe_subscription(stripe_sub)


def _reset_quota_for_invoice(stripe_invoice: dict) -> None:
    """Reset the monthly quota counter when a billing period renews."""
    from apps.billing.models import Subscription
    sub_id = stripe_invoice.get('subscription', '')
    try:
        sub = Subscription.objects.get(stripe_subscription_id=sub_id)
        from services.billing_service import reset_quota
        reset_quota(sub.user)
        logger.info('StripeWebhookView: quota reset for user %s', sub.user_id)
    except Subscription.DoesNotExist:
        pass

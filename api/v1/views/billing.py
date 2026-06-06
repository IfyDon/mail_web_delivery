"""Billing API views: overview, Stripe Checkout, Customer Portal, invoices."""
import logging

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing.serializers import (
    BillingOverviewSerializer,
    CheckoutRequestSerializer,
    CheckoutResponseSerializer,
    InvoiceSerializer,
    PortalResponseSerializer,
)
from services.billing_service import (
    create_checkout_url,
    create_portal_url,
    get_usage,
)

logger = logging.getLogger(__name__)

_FRONTEND_BASE = getattr(settings, 'FRONTEND_BASE_URL', 'http://localhost:3000')


@extend_schema(
    responses={200: BillingOverviewSerializer},
    summary='Current plan, usage, and available plans',
    tags=['Billing'],
)
class BillingOverviewView(APIView):
    def get(self, request):
        from apps.billing.models import Plan, Subscription

        try:
            sub = request.user.subscription
        except Subscription.DoesNotExist:
            sub = None

        plans = Plan.objects.filter(is_active=True)
        usage = get_usage(request.user)

        data = {
            'subscription': sub,
            'usage': usage,
            'plans': plans,
        }
        serializer = BillingOverviewSerializer(data)
        return Response(serializer.data)


@extend_schema(
    request=CheckoutRequestSerializer,
    responses={200: CheckoutResponseSerializer},
    summary='Create a Stripe Checkout session for a plan upgrade',
    tags=['Billing'],
)
class CheckoutSessionView(APIView):
    def post(self, request):
        serializer = CheckoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        success_url = data.get('success_url') or f'{_FRONTEND_BASE}/billing?checkout=success'
        cancel_url = data.get('cancel_url') or f'{_FRONTEND_BASE}/billing?checkout=cancel'

        try:
            url = create_checkout_url(
                request.user,
                plan_slug=data['plan_slug'],
                success_url=success_url,
                cancel_url=cancel_url,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning('CheckoutSessionView: %s', exc)
            return Response(
                {'detail': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({'checkout_url': url})


@extend_schema(
    responses={200: PortalResponseSerializer},
    summary='Create a Stripe Customer Portal session to manage the subscription',
    tags=['Billing'],
)
class PortalSessionView(APIView):
    def post(self, request):
        return_url = request.data.get('return_url') or f'{_FRONTEND_BASE}/billing'

        try:
            url = create_portal_url(request.user, return_url=return_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning('PortalSessionView: %s', exc)
            return Response(
                {'detail': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({'portal_url': url})


@extend_schema(
    responses={200: InvoiceSerializer(many=True)},
    summary='List invoices for the current user',
    tags=['Billing'],
)
class InvoiceListView(APIView):
    def get(self, request):
        from apps.billing.models import Invoice, Subscription

        try:
            sub = request.user.subscription
            invoices = Invoice.objects.filter(subscription=sub).order_by('-created_at')[:24]
        except Subscription.DoesNotExist:
            invoices = Invoice.objects.none()

        serializer = InvoiceSerializer(invoices, many=True)
        return Response(serializer.data)

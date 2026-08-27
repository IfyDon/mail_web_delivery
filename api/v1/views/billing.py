"""Billing API views: overview, Paystack checkout, subscription portal, invoices."""
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
    VerifyRequestSerializer,
    VerifyResponseSerializer,
)
from services.billing_service import (
    create_checkout_url,
    create_manage_url,
    get_usage,
    verify_and_sync_transaction,
)

logger = logging.getLogger(__name__)

_FRONTEND_BASE = getattr(settings, 'BASE_URL', 'http://localhost:8000')


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
    summary='Initialize a Paystack transaction and return the authorization URL',
    tags=['Billing'],
)
class CheckoutSessionView(APIView):
    def post(self, request):
        serializer = CheckoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        success_url = data.get('success_url') or f'{_FRONTEND_BASE}/dashboard/?checkout=success'
        cancel_url = data.get('cancel_url') or f'{_FRONTEND_BASE}/pricing/?checkout=cancel'

        try:
            url = create_checkout_url(
                request.user,
                plan_slug=data['plan_slug'],
                success_url=success_url,
                cancel_url=cancel_url,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning('CheckoutSessionView: %s', exc)
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'checkout_url': url})


@extend_schema(
    responses={200: PortalResponseSerializer},
    summary='Return the Paystack subscription management link',
    tags=['Billing'],
)
class PortalSessionView(APIView):
    def post(self, request):
        try:
            url = create_manage_url(request.user)
        except Exception as exc:  # noqa: BLE001
            logger.warning('PortalSessionView: %s', exc)
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'portal_url': url})


@extend_schema(
    request=VerifyRequestSerializer,
    responses={200: VerifyResponseSerializer},
    summary='Verify a Paystack transaction after the user returns from checkout',
    tags=['Billing'],
)
class VerifyTransactionView(APIView):
    """
    Called by the frontend after Paystack redirects back with ?reference=REF.
    Verifies the transaction, syncs the invoice and subscription, and returns
    the outcome.
    """

    def post(self, request):
        serializer = VerifyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reference = serializer.validated_data['reference']

        try:
            result = verify_and_sync_transaction(reference)
        except Exception as exc:  # noqa: BLE001
            logger.warning('VerifyTransactionView: %s', exc)
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(result)


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

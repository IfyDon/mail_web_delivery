"""Paystack webhook endpoint: verify signature, dispatch to billing service."""
import json
import logging

from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

from integrations.paystack.client import PaystackClient

logger = logging.getLogger(__name__)

PAYSTACK_TRUSTED_IPS = {'52.31.139.75', '52.49.173.169', '52.214.14.220'}


@method_decorator(csrf_exempt, name='dispatch')
class PaystackWebhookView(View):
    """
    POST /webhooks/paystack/

    Paystack signs every request with HMAC-SHA512 of the raw body using the
    secret key.  The signature is sent in the X-Paystack-Signature header.
    We always return 200 on application errors so Paystack does not retry.
    """

    def post(self, request, *args, **kwargs):
        self._log_ip(request)

        signature = request.headers.get('X-Paystack-Signature', '')
        raw_body = request.body

        if not PaystackClient().verify_webhook_signature(raw_body, signature):
            logger.warning('paystack_webhook: invalid signature — request rejected')
            return HttpResponse(status=400)

        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            logger.warning('paystack_webhook: non-JSON body')
            return HttpResponse(status=400)

        event = payload.get('event', '')
        data = payload.get('data', {})
        logger.info('paystack_webhook: received event=%s', event)

        try:
            self._dispatch(event, data)
        except Exception:
            logger.exception('paystack_webhook: unhandled error processing event=%s', event)

        return HttpResponse(status=200)

    # ── Dispatcher ───────────────────────────────────────────────────────────

    def _dispatch(self, event: str, data: dict) -> None:
        handlers = {
            'charge.success':        self._on_charge_success,
            'subscription.create':   self._on_subscription_create,
            'subscription.not_renew': self._on_subscription_not_renew,
            'subscription.disable':  self._on_subscription_disable,
            'subscription.enable':   self._on_subscription_enable,
            'invoice.create':        self._on_invoice_create,
            'invoice.update':        self._on_invoice_update,
        }
        handler = handlers.get(event)
        if handler:
            handler(data)
        else:
            logger.debug('paystack_webhook: no handler for event=%s', event)

    # ── Event handlers ───────────────────────────────────────────────────────

    def _on_charge_success(self, data: dict) -> None:
        from services.billing_service import sync_transaction
        sync_transaction(data)

    def _on_subscription_create(self, data: dict) -> None:
        from services.billing_service import sync_from_paystack_subscription
        sync_from_paystack_subscription(data)

    def _on_subscription_not_renew(self, data: dict) -> None:
        from services.billing_service import sync_from_paystack_subscription
        sync_from_paystack_subscription(data)

    def _on_subscription_disable(self, data: dict) -> None:
        from services.billing_service import sync_from_paystack_subscription
        sync_from_paystack_subscription(data)

    def _on_subscription_enable(self, data: dict) -> None:
        from services.billing_service import sync_from_paystack_subscription
        sync_from_paystack_subscription(data)

    def _on_invoice_create(self, data: dict) -> None:
        transaction = data.get('transaction', data)
        from services.billing_service import sync_transaction
        sync_transaction(transaction)

    def _on_invoice_update(self, data: dict) -> None:
        transaction = data.get('transaction', data)
        from services.billing_service import sync_transaction
        sync_transaction(transaction)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _log_ip(self, request) -> None:
        ip = self._client_ip(request)
        if ip not in PAYSTACK_TRUSTED_IPS:
            logger.warning('paystack_webhook: request from untrusted IP %s', ip)

    @staticmethod
    def _client_ip(request) -> str:
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')

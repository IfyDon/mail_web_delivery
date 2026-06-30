"""Thin wrapper around the Paystack REST API for billing operations."""
import hashlib
import hmac
import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

_BASE_URL = 'https://api.paystack.co'


def _get_secret_key() -> str:
    key = os.getenv('PAYSTACK_SECRET_KEY', '')
    if not key:
        raise RuntimeError('PAYSTACK_SECRET_KEY is not configured.')
    return key


class PaystackClient:
    """Encapsulates all Paystack REST API calls used by billing_service."""

    def __init__(self):
        self._secret_key = _get_secret_key()
        self._session = requests.Session()
        self._session.headers.update({
            'Authorization': f'Bearer {self._secret_key}',
            'Content-Type': 'application/json',
        })

    def _get(self, path: str, **params) -> dict:
        resp = self._session.get(f'{_BASE_URL}{path}', params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if not data.get('status'):
            raise RuntimeError(f'Paystack error on GET {path}: {data.get("message")}')
        return data

    def _post(self, path: str, **data: Any) -> dict:
        resp = self._session.post(f'{_BASE_URL}{path}', json=data, timeout=15)
        resp.raise_for_status()
        result = resp.json()
        if not result.get('status'):
            raise RuntimeError(f'Paystack error on POST {path}: {result.get("message")}')
        return result

    # ── Customers ────────────────────────────────────────────────────────

    def create_customer(self, email: str, first_name: str = '', last_name: str = '') -> str:
        """Create a Paystack customer and return their customer_code."""
        result = self._post(
            '/customer', email=email, first_name=first_name, last_name=last_name
        )
        customer_code = result['data']['customer_code']
        logger.info('PaystackClient: created customer %s for %s', customer_code, email)
        return customer_code

    # ── Transactions ─────────────────────────────────────────────────────

    def initialize_transaction(
        self,
        email: str,
        amount: int,
        plan_code: str,
        callback_url: str,
        metadata: dict | None = None,
    ) -> dict:
        """
        Initialize a Paystack payment and return {authorization_url, reference}.

        amount must be in the smallest currency unit (kobo for NGN, cents for USD).
        Passing plan_code automatically creates a subscription on successful payment.
        """
        payload: dict[str, Any] = {
            'email': email,
            'amount': amount,
            'plan': plan_code,
            'callback_url': callback_url,
        }
        if metadata:
            payload['metadata'] = metadata
        result = self._post('/transaction/initialize', **payload)
        return {
            'authorization_url': result['data']['authorization_url'],
            'reference': result['data']['reference'],
        }

    def verify_transaction(self, reference: str) -> dict:
        """Verify and return the full transaction data dict for *reference*."""
        result = self._get(f'/transaction/verify/{reference}')
        return result['data']

    # ── Subscriptions ────────────────────────────────────────────────────

    def get_subscription(self, subscription_code: str) -> dict:
        """Retrieve a subscription by its code."""
        result = self._get(f'/subscription/{subscription_code}')
        return result['data']

    def disable_subscription(self, subscription_code: str, email_token: str) -> bool:
        """Disable (cancel) a Paystack subscription using the subscription's email_token."""
        result = self._post('/subscription/disable', code=subscription_code, token=email_token)
        logger.info('PaystackClient: disabled subscription %s', subscription_code)
        return result.get('status', False)

    def enable_subscription(self, subscription_code: str, email_token: str) -> bool:
        """Re-enable a previously disabled subscription."""
        result = self._post('/subscription/enable', code=subscription_code, token=email_token)
        logger.info('PaystackClient: enabled subscription %s', subscription_code)
        return result.get('status', False)

    def get_manage_link(self, subscription_code: str) -> str:
        """Return the hosted URL where the customer can manage their subscription.
        Equivalent to Stripe Customer Portal."""
        result = self._get(f'/subscription/{subscription_code}/manage/link')
        return result['data']['link']

    # ── Transactions (billing history) ───────────────────────────────────

    def list_transactions(self, customer: str, per_page: int = 24) -> list:
        """Return recent successful transactions for *customer* (email or customer_code)."""
        result = self._get(
            '/transaction', customer=customer, perPage=per_page, status='success'
        )
        return result.get('data', [])

    # ── Webhooks ─────────────────────────────────────────────────────────

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify that a webhook payload came from Paystack.
        Paystack signs the raw request body with HMAC-SHA512 using your secret key.
        The result is sent in the X-Paystack-Signature header.
        """
        expected = hmac.new(
            self._secret_key.encode('utf-8'), payload, hashlib.sha512
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

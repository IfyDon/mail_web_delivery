"""Thin wrapper around the Stripe SDK for billing operations."""
import logging
import os

import stripe

logger = logging.getLogger(__name__)


def _get_api_key() -> str:
    key = os.getenv('STRIPE_SECRET_KEY', '')
    if not key:
        raise RuntimeError('STRIPE_SECRET_KEY is not configured.')
    return key


class StripeClient:
    """Encapsulates all Stripe API calls used by billing_service."""

    def __init__(self):
        stripe.api_key = _get_api_key()

    # ── Customers ────────────────────────────────────────────────────────

    def create_customer(self, email: str, name: str = '') -> str:
        """Create a Stripe customer and return their customer ID."""
        customer = stripe.Customer.create(email=email, name=name or email)
        logger.info('StripeClient: created customer %s for %s', customer.id, email)
        return customer.id

    # ── Checkout & Portal ────────────────────────────────────────────────

    def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """Create a Stripe Checkout session and return its URL."""
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
            allow_promotion_codes=True,
        )
        return session.url

    def create_portal_session(self, customer_id: str, return_url: str) -> str:
        """Create a Stripe Customer Portal session and return its URL."""
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return session.url

    # ── Subscriptions ────────────────────────────────────────────────────

    def cancel_subscription(self, subscription_id: str) -> None:
        """Cancel a subscription immediately."""
        stripe.Subscription.cancel(subscription_id)
        logger.info('StripeClient: cancelled subscription %s', subscription_id)

    def retrieve_subscription(self, subscription_id: str) -> stripe.Subscription:
        """Retrieve a Stripe Subscription object by ID."""
        return stripe.Subscription.retrieve(subscription_id)

    # ── Invoices ─────────────────────────────────────────────────────────

    def list_invoices(self, customer_id: str, limit: int = 24) -> list:
        """Return the latest *limit* invoices for a customer."""
        result = stripe.Invoice.list(customer=customer_id, limit=limit)
        return result.data

    # ── Webhooks ─────────────────────────────────────────────────────────

    def construct_event(self, payload: bytes, sig_header: str, secret: str) -> stripe.Event:
        """Verify a Stripe webhook signature and return the parsed Event."""
        return stripe.Webhook.construct_event(payload, sig_header, secret)

"""Billing service: quota checks, Stripe customer lifecycle, invoice sync."""
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# ── Quota helpers ────────────────────────────────────────────────────────────

def get_or_create_quota(user):
    """Return the user's Quota, creating it with defaults if absent."""
    from apps.accounts.models import Quota
    quota, _ = Quota.objects.get_or_create(
        user=user,
        defaults={'monthly_limit': _plan_limit(user)},
    )
    return quota


def get_usage(user) -> dict:
    """Return current-month usage dict: sent, limit, percent."""
    quota = get_or_create_quota(user)
    limit = quota.monthly_limit
    sent = quota.emails_sent_this_month
    percent = 0 if limit == 0 else min(100, round(sent / limit * 100))
    return {'sent': sent, 'limit': limit, 'percent': percent}


def check_quota(user) -> bool:
    """Return True if the user is within their monthly email quota."""
    quota = get_or_create_quota(user)
    if quota.monthly_limit == 0:
        return True  # 0 means unlimited
    return quota.emails_sent_this_month < quota.monthly_limit


def increment_quota(user) -> None:
    """Increment the sent counter for the current billing period."""
    from apps.accounts.models import Quota
    Quota.objects.filter(user=user).update(
        emails_sent_this_month=models_f('emails_sent_this_month') + 1
    )


def reset_quota(user) -> None:
    """Reset monthly counter to zero (called by Celery Beat at period start)."""
    from apps.accounts.models import Quota
    Quota.objects.filter(user=user).update(emails_sent_this_month=0)


def _plan_limit(user) -> int:
    """Return the email limit from the user's active subscription plan, or the free default."""
    try:
        sub = user.subscription
        limit = sub.plan.email_limit
        return limit if limit is not None else 0  # 0 = unlimited
    except AttributeError:
        return 1_000  # free tier default — subscription not yet created


# ── Stripe customer lifecycle ────────────────────────────────────────────────

def get_or_create_stripe_customer(user) -> str:
    """Return the Stripe customer ID for *user*, creating one if needed."""
    from integrations.stripe.client import StripeClient

    try:
        sub = user.subscription
        if sub.stripe_customer_id:
            return sub.stripe_customer_id
    except AttributeError:
        pass  # no subscription row yet — will create one below

    client = StripeClient()
    customer_id = client.create_customer(email=user.email, name=user.get_full_name())

    # Persist customer ID — upsert on the subscription record (or create a stub)
    _upsert_subscription_customer_id(user, customer_id)
    return customer_id


def _upsert_subscription_customer_id(user, customer_id: str) -> None:
    from apps.billing.models import Plan, Subscription
    free_plan = Plan.objects.filter(slug=Plan.SLUG_FREE).first()
    if free_plan is None:
        logger.warning('billing_service: free Plan not seeded — cannot create Subscription stub')
        return
    Subscription.objects.update_or_create(
        user=user,
        defaults={'stripe_customer_id': customer_id, 'plan': free_plan},
    )


# ── Subscription sync from Stripe ────────────────────────────────────────────

def sync_from_stripe_subscription(stripe_sub) -> None:
    """Upsert a local Subscription row from a Stripe Subscription object."""
    from apps.billing.models import Plan, Subscription

    stripe_price_id = None
    if stripe_sub.get('items') and stripe_sub['items']['data']:
        stripe_price_id = stripe_sub['items']['data'][0]['price']['id']

    plan = None
    if stripe_price_id:
        plan = Plan.objects.filter(stripe_price_id=stripe_price_id, is_active=True).first()

    # Find subscription by stripe_subscription_id or stripe_customer_id
    sub = (
        Subscription.objects.filter(stripe_subscription_id=stripe_sub['id']).first()
        or Subscription.objects.filter(stripe_customer_id=stripe_sub['customer']).first()
    )
    if sub is None:
        logger.warning(
            'billing_service: no local Subscription found for Stripe sub %s', stripe_sub['id']
        )
        return

    update_fields = {
        'stripe_subscription_id': stripe_sub['id'],
        'status': _map_stripe_status(stripe_sub['status']),
    }
    if plan:
        update_fields['plan'] = plan
        # Keep quota in sync with new plan limit
        from apps.accounts.models import Quota
        Quota.objects.filter(user=sub.user).update(
            monthly_limit=plan.email_limit if plan.email_limit is not None else 0
        )
    if stripe_sub.get('current_period_start'):
        update_fields['current_period_start'] = datetime.fromtimestamp(
            stripe_sub['current_period_start'], tz=timezone.utc
        )
    if stripe_sub.get('current_period_end'):
        update_fields['current_period_end'] = datetime.fromtimestamp(
            stripe_sub['current_period_end'], tz=timezone.utc
        )

    for key, val in update_fields.items():
        setattr(sub, key, val)
    sub.save()
    logger.info('billing_service: synced subscription %s → %s', stripe_sub['id'], sub.status)


def _map_stripe_status(stripe_status: str) -> str:
    from apps.billing.models import Subscription
    mapping = {
        'active':     Subscription.STATUS_ACTIVE,
        'past_due':   Subscription.STATUS_PAST_DUE,
        'canceled':   Subscription.STATUS_CANCELLED,
        'cancelled':  Subscription.STATUS_CANCELLED,
        'trialing':   Subscription.STATUS_TRIALING,
        'incomplete': Subscription.STATUS_INCOMPLETE,
    }
    return mapping.get(stripe_status, Subscription.STATUS_INCOMPLETE)


# ── Invoice sync ─────────────────────────────────────────────────────────────

def sync_invoice(stripe_invoice) -> None:
    """Upsert a local Invoice from a Stripe Invoice object."""
    from apps.billing.models import Invoice, Subscription

    sub = Subscription.objects.filter(
        stripe_subscription_id=stripe_invoice.get('subscription', '')
    ).first()

    Invoice.objects.update_or_create(
        stripe_invoice_id=stripe_invoice['id'],
        defaults={
            'subscription': sub,
            'amount_paid': stripe_invoice.get('amount_paid', 0),
            'currency': stripe_invoice.get('currency', 'usd'),
            'status': stripe_invoice.get('status', Invoice.STATUS_OPEN),
            'pdf_url': stripe_invoice.get('invoice_pdf', '') or '',
            'hosted_url': stripe_invoice.get('hosted_invoice_url', '') or '',
            'period_start': (
                datetime.fromtimestamp(stripe_invoice['period_start'], tz=timezone.utc)
                if stripe_invoice.get('period_start') else None
            ),
            'period_end': (
                datetime.fromtimestamp(stripe_invoice['period_end'], tz=timezone.utc)
                if stripe_invoice.get('period_end') else None
            ),
        },
    )
    logger.info(
        'billing_service: synced invoice %s (%s)',
        stripe_invoice['id'], stripe_invoice.get('status'),
    )


# ── Session helpers (called by API views) ────────────────────────────────────

def create_checkout_url(user, plan_slug: str, success_url: str, cancel_url: str) -> str:
    """Return a Stripe Checkout URL for upgrading to *plan_slug*."""
    from apps.billing.models import Plan
    from integrations.stripe.client import StripeClient

    plan = Plan.objects.get(slug=plan_slug, is_active=True)
    if not plan.stripe_price_id:
        raise ValueError(f'Plan "{plan_slug}" has no Stripe Price ID configured.')

    customer_id = get_or_create_stripe_customer(user)
    return StripeClient().create_checkout_session(
        customer_id, plan.stripe_price_id, success_url, cancel_url
    )


def create_portal_url(user, return_url: str) -> str:
    """Return a Stripe Customer Portal URL for the user."""
    from integrations.stripe.client import StripeClient
    customer_id = get_or_create_stripe_customer(user)
    return StripeClient().create_portal_session(customer_id, return_url)


# F expression import kept local to avoid Django app-loading order issues
def models_f(field: str):
    """Return a Django F() expression for *field*."""
    from django.db.models import F
    return F(field)

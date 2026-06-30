"""Billing service: quota checks, Paystack customer lifecycle, transaction sync."""
import logging
from datetime import datetime

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
        emails_sent_this_month=_f('emails_sent_this_month') + 1
    )


def reset_quota(user) -> None:
    """Reset monthly counter to zero (called on billing period renewal)."""
    from apps.accounts.models import Quota
    Quota.objects.filter(user=user).update(emails_sent_this_month=0)


def _plan_limit(user) -> int:
    """Return email limit from the user's active subscription plan, or the free default."""
    try:
        limit = user.subscription.plan.email_limit
        return limit if limit is not None else 0  # 0 = unlimited
    except AttributeError:
        return 1_000  # free tier default — subscription not yet created


# ── Paystack customer lifecycle ──────────────────────────────────────────────

def get_or_create_paystack_customer(user) -> str:
    """Return the Paystack customer_code for *user*, creating one if needed."""
    from integrations.paystack.client import PaystackClient

    try:
        sub = user.subscription
        if sub.paystack_customer_code:
            return sub.paystack_customer_code
    except AttributeError:
        pass

    name_parts = (user.get_full_name() or '').split(' ', 1)
    first = name_parts[0] if name_parts else ''
    last = name_parts[1] if len(name_parts) > 1 else ''

    customer_code = PaystackClient().create_customer(
        email=user.email, first_name=first, last_name=last
    )
    _upsert_subscription_customer_code(user, customer_code)
    return customer_code


def _upsert_subscription_customer_code(user, customer_code: str) -> None:
    from apps.billing.models import Plan, Subscription
    free_plan = Plan.objects.filter(slug=Plan.SLUG_FREE).first()
    if free_plan is None:
        logger.warning('billing_service: free Plan not seeded — cannot create Subscription stub')
        return
    Subscription.objects.update_or_create(
        user=user,
        defaults={'paystack_customer_code': customer_code, 'plan': free_plan},
    )


# ── Subscription sync from Paystack ──────────────────────────────────────────

def sync_from_paystack_subscription(ps_sub: dict) -> None:
    """Upsert a local Subscription from a Paystack subscription data dict."""
    from apps.billing.models import Plan, Subscription

    subscription_code = ps_sub.get('subscription_code', '')
    customer_code = (ps_sub.get('customer') or {}).get('customer_code', '')
    plan_code = (ps_sub.get('plan') or {}).get('plan_code', '')
    email_token = ps_sub.get('email_token', '')

    plan = Plan.objects.filter(
        paystack_plan_code=plan_code, is_active=True
    ).first() if plan_code else None

    sub = (
        Subscription.objects.filter(
            paystack_subscription_code=subscription_code
        ).first() if subscription_code else None
    ) or (
        Subscription.objects.filter(
            paystack_customer_code=customer_code
        ).first() if customer_code else None
    )

    if sub is None:
        logger.warning(
            'billing_service: no local Subscription for sub=%s customer=%s',
            subscription_code, customer_code,
        )
        return

    updates: dict = {'status': _map_paystack_status(ps_sub.get('status', ''))}
    if subscription_code:
        updates['paystack_subscription_code'] = subscription_code
    if email_token:
        updates['paystack_email_token'] = email_token
    if plan:
        updates['plan'] = plan
        from apps.accounts.models import Quota
        Quota.objects.filter(user=sub.user).update(
            monthly_limit=plan.email_limit if plan.email_limit is not None else 0
        )

    for raw_field, model_field in (
        ('created_at', 'current_period_start'),
        ('next_payment_date', 'current_period_end'),
    ):
        raw = ps_sub.get(raw_field)
        if raw:
            try:
                updates[model_field] = datetime.fromisoformat(raw.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass

    for key, val in updates.items():
        setattr(sub, key, val)
    sub.save()
    logger.info('billing_service: synced subscription %s → %s', subscription_code, sub.status)


def _map_paystack_status(ps_status: str) -> str:
    from apps.billing.models import Subscription
    return {
        'active':       Subscription.STATUS_ACTIVE,
        'non-renewing': Subscription.STATUS_CANCELLED,
        'cancelled':    Subscription.STATUS_CANCELLED,
        'attention':    Subscription.STATUS_PAST_DUE,
        'completed':    Subscription.STATUS_CANCELLED,
        'incomplete':   Subscription.STATUS_INCOMPLETE,
    }.get(ps_status, Subscription.STATUS_INCOMPLETE)


# ── Transaction sync (invoice equivalent) ────────────────────────────────────

def sync_transaction(ps_tx: dict) -> None:
    """Upsert a local Invoice from a Paystack transaction data dict."""
    from apps.billing.models import Invoice, Subscription

    reference = ps_tx.get('reference', '')
    if not reference:
        return

    subscription_code = ps_tx.get('subscription_code') or (
        (ps_tx.get('plan') or {}).get('subscription_code', '')
    )
    sub = (
        Subscription.objects.filter(
            paystack_subscription_code=subscription_code
        ).first() if subscription_code else None
    )

    ps_status = ps_tx.get('status', '')
    invoice_status = {
        'success': Invoice.STATUS_PAID,
        'failed':  Invoice.STATUS_OPEN,
    }.get(ps_status, Invoice.STATUS_OPEN)

    period_start = None
    for date_field in ('paid_at', 'created_at'):
        raw = ps_tx.get(date_field)
        if raw:
            try:
                period_start = datetime.fromisoformat(raw.replace('Z', '+00:00'))
                break
            except (ValueError, AttributeError):
                pass

    Invoice.objects.update_or_create(
        paystack_reference=reference,
        defaults={
            'subscription': sub,
            'amount_paid': ps_tx.get('amount', 0),
            'currency': ps_tx.get('currency', 'ngn').lower(),
            'status': invoice_status,
            'period_start': period_start,
        },
    )
    logger.info('billing_service: synced transaction %s (%s)', reference, ps_status)


# ── Session helpers (called by API views) ────────────────────────────────────

def create_checkout_url(user, plan_slug: str, success_url: str, cancel_url: str) -> str:
    """
    Initialize a Paystack transaction for *plan_slug* and return the authorization_url.
    The user is redirected to that URL to complete payment on Paystack's hosted page.
    On success Paystack redirects to success_url?reference=REF and fires a webhook.
    cancel_url is stored in metadata so the frontend can redirect on abandonment.
    """
    from apps.billing.models import Plan
    from integrations.paystack.client import PaystackClient

    plan = Plan.objects.get(slug=plan_slug, is_active=True)
    if not plan.paystack_plan_code:
        raise ValueError(f'Plan "{plan_slug}" has no Paystack Plan Code configured.')

    # price_monthly is in major currency units; Paystack needs the smallest unit (×100)
    amount = int(plan.price_monthly * 100)

    _ = get_or_create_paystack_customer(user)  # ensures customer record exists

    tx = PaystackClient().initialize_transaction(
        email=user.email,
        amount=amount,
        plan_code=plan.paystack_plan_code,
        callback_url=success_url,
        metadata={
            'user_id': str(user.pk),
            'plan_slug': plan_slug,
            'cancel_url': cancel_url,
        },
    )
    logger.info(
        'billing_service: initialized Paystack transaction for user=%s plan=%s',
        user.pk, plan_slug,
    )
    return tx['authorization_url']


def create_manage_url(user) -> str:
    """Return the Paystack subscription manage URL (equivalent of Stripe Customer Portal)."""
    from integrations.paystack.client import PaystackClient

    try:
        sub = user.subscription
        if not sub.paystack_subscription_code:
            raise ValueError('No active Paystack subscription found.')
        return PaystackClient().get_manage_link(sub.paystack_subscription_code)
    except AttributeError as exc:
        raise ValueError('User has no subscription.') from exc


def verify_and_sync_transaction(reference: str) -> dict:
    """
    Verify a Paystack transaction by reference, sync the invoice and subscription,
    and return a summary dict {status, plan, subscription_status}.
    Called by the billing/verify/ endpoint after the user returns from Paystack checkout.
    """
    from integrations.paystack.client import PaystackClient

    tx = PaystackClient().verify_transaction(reference)
    sync_transaction(tx)

    plan_code = (tx.get('plan') or {}).get('plan_code', '')
    plan_name = (tx.get('plan') or {}).get('name', '')

    subscription_status = ''
    sub_code = tx.get('subscription_code', '')
    if sub_code:
        from apps.billing.models import Subscription
        try:
            sub = Subscription.objects.get(paystack_subscription_code=sub_code)
            subscription_status = sub.status
        except Subscription.DoesNotExist:
            pass

    if tx.get('status') == 'success' and sub_code:
        from apps.billing.models import Subscription
        try:
            sub = Subscription.objects.get(paystack_subscription_code=sub_code)
            reset_quota(sub.user)
        except Subscription.DoesNotExist:
            pass

    return {
        'status': tx.get('status', ''),
        'plan': plan_name or plan_code,
        'subscription_status': subscription_status,
    }


# ── Internal helpers ─────────────────────────────────────────────────────────

def _f(field: str):
    from django.db.models import F
    return F(field)

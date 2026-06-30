"""Billing models: Plan, Subscription, Invoice."""
from django.conf import settings
from django.db import models


class Plan(models.Model):
    """A pricing tier offered by the platform."""

    SLUG_FREE = 'free'
    SLUG_STARTUP = 'startup'
    SLUG_ENTERPRISE = 'enterprise'

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    price_monthly = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    email_limit = models.IntegerField(
        null=True, blank=True,
        help_text='Monthly email quota. NULL means unlimited.',
    )
    paystack_plan_code = models.CharField(
        max_length=255, blank=True,
        help_text='Paystack Plan Code (e.g. PLN_XXXX). Empty for free plan.',
    )
    is_active = models.BooleanField(default=True)
    features = models.JSONField(default=list, help_text='List of feature strings shown in UI.')

    class Meta:
        ordering = ['price_monthly']

    def __str__(self):
        return self.name


class Subscription(models.Model):
    """One active (or cancelled) subscription per user."""

    STATUS_ACTIVE = 'active'
    STATUS_PAST_DUE = 'past_due'
    STATUS_CANCELLED = 'cancelled'
    STATUS_TRIALING = 'trialing'
    STATUS_INCOMPLETE = 'incomplete'

    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_PAST_DUE, 'Past Due'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_TRIALING, 'Trialing'),
        (STATUS_INCOMPLETE, 'Incomplete'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription',
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='subscriptions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)

    paystack_customer_code = models.CharField(max_length=255, blank=True, db_index=True)
    paystack_subscription_code = models.CharField(max_length=255, blank=True, db_index=True)
    paystack_email_token = models.CharField(
        max_length=255, blank=True,
        help_text='Required by Paystack to enable/disable this subscription.',
    )

    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} → {self.plan.name} ({self.status})'

    @property
    def is_active(self):
        return self.status in (self.STATUS_ACTIVE, self.STATUS_TRIALING)


class Invoice(models.Model):
    """A billing record synced from Paystack transactions."""

    STATUS_PAID = 'paid'
    STATUS_OPEN = 'open'
    STATUS_VOID = 'void'
    STATUS_UNCOLLECTIBLE = 'uncollectible'

    STATUS_CHOICES = [
        (STATUS_PAID, 'Paid'),
        (STATUS_OPEN, 'Open'),
        (STATUS_VOID, 'Void'),
        (STATUS_UNCOLLECTIBLE, 'Uncollectible'),
    ]

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='invoices',
        null=True, blank=True,
    )
    paystack_reference = models.CharField(max_length=255, unique=True)
    amount_paid = models.IntegerField(
        default=0, help_text='Amount in smallest currency unit (kobo for NGN, cents for USD).'
    )
    currency = models.CharField(max_length=3, default='ngn')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
    pdf_url = models.URLField(blank=True)
    hosted_url = models.URLField(blank=True)
    period_start = models.DateTimeField(null=True, blank=True)
    period_end = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.paystack_reference} — {self.status}'

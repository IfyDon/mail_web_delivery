"""Serializers for billing overview, plans, subscriptions, and invoices."""
from rest_framework import serializers

from apps.billing.models import Invoice, Plan, Subscription


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ['id', 'name', 'slug', 'price_monthly', 'email_limit', 'features']


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = ['id', 'plan', 'status', 'current_period_start', 'current_period_end']


class InvoiceSerializer(serializers.ModelSerializer):
    amount_display = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'paystack_reference', 'amount_paid', 'amount_display',
            'currency', 'status', 'pdf_url', 'hosted_url',
            'period_start', 'period_end', 'created_at',
        ]

    def get_amount_display(self, obj):
        """Return amount formatted in major currency units, e.g. '₦500.00'."""
        symbols = {'ngn': '₦', 'usd': '$', 'ghs': '₵', 'kes': 'KSh ', 'zar': 'R'}
        symbol = symbols.get(obj.currency.lower(), obj.currency.upper() + ' ')
        return f'{symbol}{obj.amount_paid / 100:.2f}'


class BillingOverviewSerializer(serializers.Serializer):
    subscription = SubscriptionSerializer(allow_null=True)
    usage = serializers.DictField()
    plans = PlanSerializer(many=True)


class CheckoutRequestSerializer(serializers.Serializer):
    plan_slug = serializers.CharField()
    success_url = serializers.URLField(required=False)
    cancel_url = serializers.URLField(required=False)


class CheckoutResponseSerializer(serializers.Serializer):
    checkout_url = serializers.URLField()


class PortalResponseSerializer(serializers.Serializer):
    portal_url = serializers.URLField()


class VerifyRequestSerializer(serializers.Serializer):
    reference = serializers.CharField()


class VerifyResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    plan = serializers.CharField(allow_blank=True)
    subscription_status = serializers.CharField()

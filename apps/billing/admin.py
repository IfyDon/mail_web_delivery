from django.contrib import admin

from .models import Invoice, Plan, Subscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'price_monthly', 'email_limit', 'stripe_price_id', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'slug', 'stripe_price_id']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'plan', 'status',
        'stripe_customer_id', 'stripe_subscription_id',
        'current_period_end', 'created_at',
    ]
    list_filter = ['status', 'plan']
    search_fields = ['user__email', 'stripe_customer_id', 'stripe_subscription_id']
    raw_id_fields = ['user']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'stripe_invoice_id', 'subscription', 'amount_paid',
        'currency', 'status', 'created_at',
    ]
    list_filter = ['status', 'currency']
    search_fields = ['stripe_invoice_id', 'subscription__user__email']
    raw_id_fields = ['subscription']
    readonly_fields = ['created_at']

from django.contrib import admin

from .models import Invoice, Plan, Subscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'price_monthly', 'email_limit', 'paystack_plan_code',
                    'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'slug', 'paystack_plan_code']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'plan', 'status',
        'paystack_customer_code', 'paystack_subscription_code',
        'current_period_end', 'created_at',
    ]
    list_filter = ['status', 'plan']
    search_fields = ['user__email', 'paystack_customer_code', 'paystack_subscription_code']
    raw_id_fields = ['user']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'paystack_reference', 'subscription', 'amount_paid',
        'currency', 'status', 'created_at',
    ]
    list_filter = ['status', 'currency']
    search_fields = ['paystack_reference', 'subscription__user__email']
    raw_id_fields = ['subscription']
    readonly_fields = ['created_at']

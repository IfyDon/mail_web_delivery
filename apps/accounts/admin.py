from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import APIKey, AuditLog, CustomUser, IPWhitelist, Quota


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'username', 'is_verified', 'is_active', 'is_staff', 'created_at']
    list_filter = ['is_verified', 'is_active', 'is_staff']
    search_fields = ['email', 'username']
    ordering = ['-created_at']
    fieldsets = UserAdmin.fieldsets + (
        ('WebMail', {'fields': ('is_verified',)}),
    )


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = [
        'prefix', 'name', 'user', 'is_active', 'rate_limit', 'last_used_at', 'created_at',
    ]
    list_filter = ['is_active']
    search_fields = ['prefix', 'name', 'user__email']
    readonly_fields = ['prefix', 'hashed_key', 'created_at', 'last_used_at']
    raw_id_fields = ['user']


@admin.register(Quota)
class QuotaAdmin(admin.ModelAdmin):
    list_display = ['user', 'emails_sent_this_month', 'monthly_limit', 'reset_date']
    search_fields = ['user__email']
    raw_id_fields = ['user']
    readonly_fields = ['reset_date']


@admin.register(IPWhitelist)
class IPWhitelistAdmin(admin.ModelAdmin):
    list_display = ['user', 'ip_address', 'label', 'created_at']
    search_fields = ['user__email', 'ip_address', 'label']
    raw_id_fields = ['user']
    readonly_fields = ['created_at']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'resource_type', 'ip_address', 'created_at']
    list_filter = ['resource_type', 'created_at']
    search_fields = ['user__email', 'action', 'resource_id', 'ip_address']
    raw_id_fields = ['user']
    readonly_fields = ['user', 'action', 'resource_type', 'resource_id',
                       'ip_address', 'user_agent', 'metadata', 'created_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

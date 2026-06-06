from django.contrib import admin

from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'from_address', 'to_address', 'subject',
        'status', 'stream', 'attempts', 'created_at',
    ]
    list_filter = ['status', 'stream', 'created_at']
    search_fields = ['to_address', 'from_address', 'subject', 'provider_message_id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']
    raw_id_fields = ['user', 'domain', 'template_version']

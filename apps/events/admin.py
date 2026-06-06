from django.contrib import admin

from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['id', 'message_id', 'type', 'timestamp']
    list_filter = ['type', 'timestamp']
    search_fields = ['message__to_address', 'message__subject']
    readonly_fields = ['timestamp']
    raw_id_fields = ['message']

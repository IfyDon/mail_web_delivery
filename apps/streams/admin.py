from django.contrib import admin

from .models import Stream


@admin.register(Stream)
class StreamAdmin(admin.ModelAdmin):
    list_display = ['slug', 'name', 'user', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['slug', 'name', 'user__email']
    prepopulated_fields = {'slug': ('name',)}
    raw_id_fields = ['user']
    readonly_fields = ['created_at']

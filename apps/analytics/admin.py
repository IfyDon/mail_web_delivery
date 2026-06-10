from django.contrib import admin

from .models import ContactEngagement, DailyStats, HourlyStats


@admin.register(DailyStats)
class DailyStatsAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'date', 'stream',
        'sent', 'delivered', 'opened', 'clicked', 'bounced', 'complained',
    ]
    list_filter = ['date', 'stream']
    search_fields = ['user__email']
    ordering = ['-date']
    raw_id_fields = ['user']


@admin.register(HourlyStats)
class HourlyStatsAdmin(admin.ModelAdmin):
    list_display = ['user', 'hour', 'sent', 'delivered', 'opened', 'clicked']
    list_filter = ['hour']
    search_fields = ['user__email']
    ordering = ['-hour']
    raw_id_fields = ['user']


@admin.register(ContactEngagement)
class ContactEngagementAdmin(admin.ModelAdmin):
    list_display = [
        'email', 'user', 'score',
        'open_count', 'click_count', 'bounce_count', 'complaint_count',
        'last_event', 'updated_at',
    ]
    list_filter = ['updated_at']
    search_fields = ['email', 'user__email']
    raw_id_fields = ['user']
    readonly_fields = ['score', 'open_count', 'click_count', 'bounce_count',
                       'complaint_count', 'last_open', 'last_click', 'last_event', 'updated_at']

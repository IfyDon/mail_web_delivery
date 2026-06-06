from django.contrib import admin

from .models import DailyStats, HourlyStats


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

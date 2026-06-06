"""Pre-aggregated stats tables — populated nightly by aggregate_daily_stats Celery Beat task."""

from django.conf import settings
from django.db import models


class DailyStats(models.Model):
    """One row per (user, date, stream) — rolled up from the Event table each night."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='daily_stats',
    )
    date = models.DateField(db_index=True)
    stream = models.CharField(max_length=50, blank=True, default='')

    sent = models.PositiveIntegerField(default=0)
    delivered = models.PositiveIntegerField(default=0)
    opened = models.PositiveIntegerField(default=0)
    clicked = models.PositiveIntegerField(default=0)
    bounced = models.PositiveIntegerField(default=0)
    complained = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'date', 'stream')
        indexes = [
            models.Index(fields=['user', 'date']),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"DailyStats({self.user_id}, {self.date}, {self.stream or 'all'})"


class HourlyStats(models.Model):
    """One row per (user, hour) — optional finer resolution for real-time dashboards."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hourly_stats',
    )
    hour = models.DateTimeField(db_index=True)

    sent = models.PositiveIntegerField(default=0)
    delivered = models.PositiveIntegerField(default=0)
    opened = models.PositiveIntegerField(default=0)
    clicked = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'hour')
        indexes = [
            models.Index(fields=['user', 'hour']),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"HourlyStats({self.user_id}, {self.hour})"

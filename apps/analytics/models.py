"""Pre-aggregated stats tables — populated nightly by aggregate_daily_stats Celery Beat task."""

from django.conf import settings
from django.db import models
from django.utils import timezone


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


class ContactEngagement(models.Model):
    """Per-contact engagement score for a given account owner.

    Updated incrementally on every open/click/bounce/complaint event.
    Score decays 10 % per month via a Celery Beat task.
    """

    SCORE_WEIGHTS = {
        'open': 2,
        'click': 5,
        'bounce': -10,
        'complaint': -50,
    }

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='contact_engagements',
        db_index=True,
    )
    email = models.EmailField(db_index=True)

    score = models.IntegerField(default=0)
    open_count = models.PositiveIntegerField(default=0)
    click_count = models.PositiveIntegerField(default=0)
    bounce_count = models.PositiveIntegerField(default=0)
    complaint_count = models.PositiveIntegerField(default=0)

    last_open = models.DateTimeField(null=True, blank=True)
    last_click = models.DateTimeField(null=True, blank=True)
    last_event = models.DateTimeField(null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'email')
        indexes = [
            models.Index(fields=['user', 'score']),
            models.Index(fields=['user', 'email']),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"ContactEngagement({self.user_id}, {self.email}, score={self.score})"

    def apply_event(self, event_type: str) -> None:
        """Increment counters and adjust score for *event_type* in-place (no save)."""
        now = timezone.now()
        weight = self.SCORE_WEIGHTS.get(event_type, 0)
        self.score += weight
        self.last_event = now
        if event_type == 'open':
            self.open_count += 1
            self.last_open = now
        elif event_type == 'click':
            self.click_count += 1
            self.last_click = now
        elif event_type == 'bounce':
            self.bounce_count += 1
        elif event_type == 'complaint':
            self.complaint_count += 1

from django.conf import settings
from django.db import models
import uuid


# ── Raw event tables (append-only inbound records from ESP) ──────────────────

class Bounce(models.Model):
    email = models.EmailField(db_index=True)
    reason = models.TextField(blank=True)
    smtp_code = models.CharField(max_length=50, blank=True)
    raw = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"Bounce:{self.email}"


class Complaint(models.Model):
    email = models.EmailField(db_index=True)
    feedback_type = models.CharField(max_length=100, blank=True)
    raw = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"Complaint:{self.email}"


class Unsubscribe(models.Model):
    email = models.EmailField(db_index=True)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    source = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("email", "token")

    def __str__(self) -> str:  # pragma: no cover
        return f"Unsubscribe:{self.email}"


# ── Per-user suppression lookup table ────────────────────────────────────────

class Suppression(models.Model):
    """Unified per-user suppression list.

    Checked before every send. Populated automatically by the inbound SES/SNS
    handler (hard bounces, complaints) and the one-click unsubscribe flow.
    Users can also remove entries manually via the dashboard or API.
    """

    REASON_BOUNCE = 'bounce'
    REASON_COMPLAINT = 'complaint'
    REASON_UNSUBSCRIBE = 'unsubscribe'
    REASON_CHOICES = [
        (REASON_BOUNCE, 'Bounce'),
        (REASON_COMPLAINT, 'Complaint'),
        (REASON_UNSUBSCRIBE, 'Unsubscribe'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='suppressions',
    )
    email = models.EmailField()
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'email')
        indexes = [
            models.Index(fields=['user', 'email']),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Suppression({self.user_id}, {self.email}, {self.reason})"

import secrets

from django.conf import settings
from django.db import models


class Webhook(models.Model):
    EVENT_DELIVERED = 'delivered'
    EVENT_OPEN = 'open'
    EVENT_CLICK = 'click'
    EVENT_BOUNCE = 'bounce'
    EVENT_COMPLAINT = 'complaint'
    EVENT_UNSUBSCRIBE = 'unsubscribe'
    EVENT_PERMANENTLY_FAILED = 'permanently_failed'

    ALL_EVENT_TYPES = [
        EVENT_DELIVERED,
        EVENT_OPEN,
        EVENT_CLICK,
        EVENT_BOUNCE,
        EVENT_COMPLAINT,
        EVENT_UNSUBSCRIBE,
        EVENT_PERMANENTLY_FAILED,
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='webhooks',
    )
    url = models.URLField(max_length=2000)
    # Shared secret for HMAC-SHA256 signing — shown once on creation
    secret = models.CharField(max_length=64, default=secrets.token_hex)
    # JSON list of event type strings the subscriber wants to receive
    event_types = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Webhook({self.url[:60]}, user={self.user_id})'

    def listens_to(self, event_type: str) -> bool:
        return event_type in self.event_types


class WebhookDispatchLog(models.Model):
    webhook = models.ForeignKey(
        Webhook,
        on_delete=models.CASCADE,
        related_name='dispatch_logs',
    )
    event_type = models.CharField(max_length=50)
    payload = models.JSONField()
    response_status = models.IntegerField(null=True, blank=True)
    # Truncated response body for debugging (max 2 KB)
    response_body = models.TextField(blank=True)
    attempts = models.IntegerField(default=0)
    succeeded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_attempted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f'Log(webhook={self.webhook_id}, event={self.event_type}, '
            f'status={self.response_status}, ok={self.succeeded})'
        )

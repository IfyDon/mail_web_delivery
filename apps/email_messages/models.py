import uuid

from django.conf import settings
from django.db import models


class Message(models.Model):
    STATUS_QUEUED = 'queued'
    STATUS_SCHEDULED = 'scheduled'
    STATUS_SENDING = 'sending'
    STATUS_SENT = 'sent'
    STATUS_DELIVERED = 'delivered'
    STATUS_FAILED = 'failed'
    STATUS_PERMANENTLY_FAILED = 'permanently_failed'
    STATUS_SUPPRESSED = 'suppressed'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_QUEUED, 'Queued'),
        (STATUS_SCHEDULED, 'Scheduled'),
        (STATUS_SENDING, 'Sending'),
        (STATUS_SENT, 'Sent'),
        (STATUS_DELIVERED, 'Delivered'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_PERMANENTLY_FAILED, 'Permanently Failed'),
        (STATUS_SUPPRESSED, 'Suppressed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    STREAM_TRANSACTIONAL = 'transactional'
    STREAM_PROMOTIONAL = 'promotional'
    STREAM_CHOICES = [
        (STREAM_TRANSACTIONAL, 'Transactional'),
        (STREAM_PROMOTIONAL, 'Promotional'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='messages',
        db_index=True,
    )
    domain = models.ForeignKey(
        'domains.Domain',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='messages',
    )
    template_version = models.ForeignKey(
        'email_templates.TemplateVersion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='messages',
    )

    to_address = models.EmailField()
    from_address = models.EmailField()
    reply_to = models.EmailField(blank=True)
    cc_addresses = models.JSONField(default=list, blank=True)
    bcc_addresses = models.JSONField(default=list, blank=True)
    subject = models.CharField(max_length=998)
    html_body = models.TextField(blank=True)
    text_body = models.TextField(blank=True)

    stream = models.CharField(
        max_length=20,
        choices=STREAM_CHOICES,
        default=STREAM_TRANSACTIONAL,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_QUEUED,
        db_index=True,
    )
    attempts = models.IntegerField(default=0)

    track_opens = models.BooleanField(default=True)
    track_clicks = models.BooleanField(default=True)

    # Populated after successful relay
    provider_message_id = models.CharField(max_length=255, blank=True)

    # Scheduled send — None means dispatch immediately
    scheduled_at = models.DateTimeField(null=True, blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['status', 'scheduled_at']),
        ]

    def __str__(self):
        return f'{self.from_address} → {self.to_address} [{self.status}]'


class MessageAttachment(models.Model):
    """A file attached to a Message, uploaded as base64 content via the send API."""

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='attachments/%Y/%m/%d/')
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100, default='application/octet-stream')
    size = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.filename} ({self.size} bytes) on {self.message_id}'

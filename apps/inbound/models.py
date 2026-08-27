"""Inbound email routing: per-domain address rules and the mail they catch."""
from django.conf import settings
from django.db import models


class InboundRoute(models.Model):
    """Routes mail addressed to a domain (or one address on it) to a webhook."""

    MATCH_EXACT = 'exact'
    MATCH_WILDCARD = 'wildcard'
    MATCH_CHOICES = [
        (MATCH_EXACT, 'One address'),
        (MATCH_WILDCARD, 'Entire domain'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='inbound_routes',
    )
    domain = models.ForeignKey(
        'domains.Domain', on_delete=models.CASCADE, related_name='inbound_routes',
    )
    match_type = models.CharField(max_length=10, choices=MATCH_CHOICES, default=MATCH_WILDCARD)
    # Local part only (the bit before @), e.g. "support". Blank when match_type is wildcard.
    local_part = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [('domain', 'local_part')]

    def __str__(self):
        return self.address

    @property
    def address(self) -> str:
        return f"{self.local_part}@{self.domain.domain}" if self.local_part else f"*@{self.domain.domain}"

    def matches(self, local_part: str) -> bool:
        if self.match_type == self.MATCH_WILDCARD:
            return True
        return self.local_part.lower() == local_part.lower()


class InboundMessage(models.Model):
    """One piece of mail received for a domain with inbound routing configured."""

    STATUS_ROUTED = 'routed'
    STATUS_FORWARDED = 'forwarded'
    STATUS_FORWARD_FAILED = 'forward_failed'
    STATUS_UNROUTED = 'unrouted'
    STATUS_CHOICES = [
        (STATUS_ROUTED, 'Routed'),
        (STATUS_FORWARDED, 'Forwarded'),
        (STATUS_FORWARD_FAILED, 'Forward failed'),
        (STATUS_UNROUTED, 'Unrouted'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True,
        related_name='inbound_messages',
    )
    route = models.ForeignKey(
        InboundRoute, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages',
    )
    ses_message_id = models.CharField(max_length=255, blank=True, db_index=True)
    from_address = models.EmailField()
    to_address = models.EmailField()
    subject = models.CharField(max_length=998, blank=True)
    text_body = models.TextField(blank=True)
    html_body = models.TextField(blank=True)
    headers = models.JSONField(default=dict, blank=True)
    spam_verdict = models.CharField(max_length=20, blank=True)
    virus_verdict = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ROUTED)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-received_at']

    def __str__(self):
        return f"{self.from_address} -> {self.to_address}: {self.subject[:40]}"


class InboundAttachment(models.Model):
    message = models.ForeignKey(InboundMessage, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='inbound_attachments/%Y/%m/')
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100, default='application/octet-stream')
    size = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.filename

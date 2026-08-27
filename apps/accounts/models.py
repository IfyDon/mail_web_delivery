from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.crypto import get_random_string
import hashlib
import ipaddress


class CustomUser(AbstractUser):
    """Custom user model for Web Mail accounts."""
    email = models.EmailField(unique=True)
    is_verified = models.BooleanField(default=False)
    sending_paused = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.email


class APIKey(models.Model):
    """API key for programmatic access with rate limiting."""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='api_keys')
    name = models.CharField(max_length=255, help_text="Friendly name for this key")
    prefix = models.CharField(max_length=20, unique=True, editable=False)  # e.g., "sk_live_"
    hashed_key = models.CharField(max_length=255, unique=True, editable=False)  # SHA256 hash
    rate_limit = models.IntegerField(default=1000, help_text="Requests per hour")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.prefix}... ({self.name})"

    @classmethod
    def generate_key(cls):
        """Generate a new API key and return both key and hashed version.

        The hash must cover the *full* raw key (prefix + suffix) — that's the
        exact string clients send as `Authorization: Bearer <raw_key>`, and
        what core.authentication.APIKeyAuthentication hashes to look it up.
        Hashing only the suffix here would make every generated key
        permanently unable to authenticate.
        """
        key = get_random_string(32, allowed_chars='abcdefghijklmnopqrstuvwxyz0123456789')
        prefix = 'sk_live_' + get_random_string(8)
        raw_key = f"{prefix}{key}"
        hashed = hashlib.sha256(raw_key.encode()).hexdigest()
        return raw_key, prefix, hashed

    def save(self, *args, **kwargs):
        if not self.prefix or not self.hashed_key:
            raise ValueError("Use generate_key() to create a new API key")
        super().save(*args, **kwargs)


class Quota(models.Model):
    """Track usage quotas for each user."""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='quota')
    emails_sent_this_month = models.IntegerField(default=0)
    monthly_limit = models.IntegerField(default=10000)
    reset_date = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = "Quota"
        verbose_name_plural = "Quotas"

    def __str__(self):
        return f"{self.user.email}: {self.emails_sent_this_month}/{self.monthly_limit}"


class IPWhitelist(models.Model):
    """Per-user IP allowlist. When entries exist, API requests from unlisted IPs are blocked."""

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='ip_whitelist')
    ip_address = models.GenericIPAddressField(protocol='both', unpack_ipv4=True)
    label = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'ip_address')
        verbose_name = "IP Whitelist Entry"
        verbose_name_plural = "IP Whitelist Entries"

    def __str__(self):
        return f"{self.user.email} — {self.ip_address}"

    @staticmethod
    def ip_matches(stored: str, client: str) -> bool:
        """Compare IPs, normalising IPv4-mapped IPv6 addresses."""
        try:
            return ipaddress.ip_address(stored) == ipaddress.ip_address(client)
        except ValueError:
            return stored == client


class AuditLog(models.Model):
    """Immutable log of write operations performed by authenticated users."""

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
    )
    action = models.CharField(max_length=200, db_index=True)
    resource_type = models.CharField(max_length=100, blank=True)
    resource_id = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['action', 'created_at']),
        ]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"

    def __str__(self):
        return f"[{self.created_at}] {self.user_id} — {self.action}"

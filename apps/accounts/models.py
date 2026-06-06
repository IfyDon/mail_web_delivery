from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.crypto import get_random_string
import hashlib


class CustomUser(AbstractUser):
    """Custom user model for Web Mail accounts."""
    email = models.EmailField(unique=True)
    is_verified = models.BooleanField(default=False)
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
        """Generate a new API key and return both key and hashed version."""
        key = get_random_string(32, allowed_chars='abcdefghijklmnopqrstuvwxyz0123456789')
        prefix = 'sk_live_' + get_random_string(8)
        hashed = hashlib.sha256(key.encode()).hexdigest()
        return f"{prefix}{key}", prefix, hashed

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

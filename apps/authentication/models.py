import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class TeamMember(models.Model):
    ROLE_ADMIN = 'admin'
    ROLE_VIEWER = 'viewer'
    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Admin'),
        (ROLE_VIEWER, 'Viewer'),
    ]

    account_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='team_members',
    )
    # Null until the invite is accepted and linked to an existing/new user
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='team_memberships',
        null=True,
        blank=True,
    )
    email = models.EmailField()
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_VIEWER)
    invited_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    # 64-char hex token (HMAC-signed equivalent; unique enforces single-use)
    invite_token = models.CharField(max_length=64, unique=True)

    class Meta:
        unique_together = ('account_owner', 'email')
        ordering = ['invited_at']

    def __str__(self):
        return f"TeamMember({self.email}, role={self.role})"

    @property
    def is_pending(self):
        return self.accepted_at is None

    @property
    def is_expired(self):
        if self.accepted_at:
            return False
        return timezone.now() > self.invited_at + timedelta(hours=48)

    @staticmethod
    def generate_invite_token():
        return secrets.token_hex(32)

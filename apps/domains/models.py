"""Domain models for email sending."""
from django.db import models
from apps.accounts.models import CustomUser


class Domain(models.Model):
    """Email sending domain with DNS verification."""

    VERIFICATION_STATUS_CHOICES = [
        ('unverified', 'Unverified'),
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='domains'
    )
    domain = models.CharField(max_length=255, unique=True)
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS_CHOICES,
        default='unverified'
    )

    # DNS Records
    spf_verified = models.BooleanField(default=False)
    dkim_verified = models.BooleanField(default=False)
    dmarc_verified = models.BooleanField(default=False)

    # DKIM Key Storage
    dkim_private_key = models.TextField(blank=True, null=True)
    dkim_public_key = models.TextField(blank=True, null=True)
    dkim_selector = models.CharField(max_length=50, default='default')

    # Verification Tokens
    verification_token = models.CharField(max_length=255, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Domain"
        verbose_name_plural = "Domains"
        ordering = ['-created_at']
        unique_together = [('user', 'domain')]

    def __str__(self):
        return f"{self.domain} ({self.get_verification_status_display()})"

    @property
    def is_fully_verified(self):
        """Check if all DNS records are verified."""
        return self.spf_verified and self.dkim_verified and self.dmarc_verified

    def generate_dkim_keys(self):
        """Generate DKIM key pair (RSA 2048)."""
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        # Extract public key
        public_key = private_key.public_key()

        # Serialize keys
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')

        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')

        self.dkim_private_key = private_pem
        self.dkim_public_key = public_pem
        self.save()

        return private_pem, public_pem

    def get_dns_instructions(self):
        """Get DNS record instructions for verification."""
        dkim_selector = self.dkim_selector
        instructions = {
            'spf': {
                'record_type': 'TXT',
                'host': self.domain,
                'value': 'v=spf1 include:mail.webmail.com ~all'
            },
            'dkim': {
                'record_type': 'TXT',
                'host': f'{dkim_selector}._domainkey.{self.domain}',
                'value': f'v=DKIM1; p={self.dkim_public_key}' if self.dkim_public_key else 'Generate DKIM keys first'
            },
            'dmarc': {
                'record_type': 'TXT',
                'host': f'_dmarc.{self.domain}',
                'value': f'v=DMARC1; p=quarantine; rua=mailto:dmarc@{self.domain}'
            }
        }
        return instructions


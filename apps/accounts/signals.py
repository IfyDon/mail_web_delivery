from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import Quota


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_quota_for_new_user(sender, instance, created, **kwargs):
    """Every new account needs a Quota row — nothing else provisions one,
    and the API views assume it exists rather than defaulting gracefully."""
    if created:
        Quota.objects.get_or_create(user=instance)

"""Message stream model — per-user configurable sending channels."""
from django.conf import settings
from django.db import models


class Stream(models.Model):
    """A named sending channel (e.g. transactional, promotional) owned by a user.

    The Message.stream CharField stores the stream slug directly so that
    delivery statistics and filtering work even if a Stream record is later
    renamed or deleted.
    """

    SLUG_TRANSACTIONAL = 'transactional'
    SLUG_PROMOTIONAL = 'promotional'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='streams',
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=50)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'slug')
        ordering = ['name']

    def __str__(self):
        return f'{self.user_id}:{self.slug}'

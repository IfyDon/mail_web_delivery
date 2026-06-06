from django.contrib.auth.backends import ModelBackend

from apps.accounts.models import CustomUser


class EmailBackend(ModelBackend):
    """Authenticate with email address instead of username."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = kwargs.get('email') or username
        if not email or not password:
            return None
        try:
            user = CustomUser.objects.get(email__iexact=email)
        except CustomUser.DoesNotExist:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

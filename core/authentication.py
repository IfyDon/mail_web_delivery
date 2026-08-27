"""
Custom DRF authentication using hashed API keys.
"""
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from apps.accounts.models import APIKey
import hashlib
from django.utils import timezone


class APIKeyAuthentication(BaseAuthentication):
    """
    Authenticate requests using API keys.
    Expected format: Authorization: Bearer sk_live_XXXXX...YYYYY
    """
    
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header.startswith('Bearer '):
            return None  # Let other authentication methods handle it
        
        try:
            key = auth_header.split(' ')[1]
        except IndexError:
            raise AuthenticationFailed('Invalid authorization header.')
        
        # Hash the key and look it up
        hashed_key = hashlib.sha256(key.encode()).hexdigest()
        
        try:
            api_key = APIKey.objects.get(hashed_key=hashed_key, is_active=True)
        except APIKey.DoesNotExist:
            raise AuthenticationFailed('Invalid or inactive API key.')
        
        # Update last used timestamp
        api_key.last_used_at = timezone.now()
        api_key.save(update_fields=['last_used_at'])
        
        # Return (user, auth) tuple
        return (api_key.user, api_key)

    def authenticate_header(self, request):
        # Without this, DRF has no authenticator to source a WWW-Authenticate
        # header from (SessionAuthentication doesn't provide one either) and
        # coerces every anonymous request's 401 NotAuthenticated to 403 —
        # see rest_framework.views.APIView.handle_exception. This is the
        # primary auth method for the API, so it should be the one DRF asks.
        return 'Bearer'

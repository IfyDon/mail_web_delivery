"""Custom DRF throttle: 100 requests/minute scoped to individual API keys."""
from rest_framework.throttling import SimpleRateThrottle


class PerAPIKeyThrottle(SimpleRateThrottle):
    scope = "api_key"

    def get_cache_key(self, request, view):
        # Scope to the API key UUID when authenticated via APIKeyAuthentication,
        # otherwise fall back to user PK (session/token auth).
        auth = request.auth
        if auth and hasattr(auth, "pk"):
            ident = str(auth.pk)
        elif request.user and request.user.is_authenticated:
            ident = str(request.user.pk)
        else:
            return None
        return self.cache_format % {"scope": self.scope, "ident": ident}

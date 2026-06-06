# Attaches validated APIKey instance to request for downstream use
from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta


class APIKeyRateLimitMiddleware:
    """
    Rate limiting middleware that enforces per-API-key rate limits.
    Uses Django's cache to track request counts per hour.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only apply rate limiting to API endpoints with API key auth
        if hasattr(request, 'auth') and hasattr(request.auth, 'rate_limit'):
            api_key = request.auth
            user = request.user
            
            # Create cache key: "ratelimit:api_key_id:YYYY-MM-DD-HH"
            now = timezone.now()
            hour_key = now.strftime('%Y-%m-%d-%H')
            cache_key = f"ratelimit:{api_key.id}:{hour_key}"
            
            # Get current request count
            request_count = cache.get(cache_key, 0)
            
            # Check if rate limit exceeded
            if request_count >= api_key.rate_limit:
                return JsonResponse(
                    {
                        'error': 'Rate limit exceeded',
                        'limit': api_key.rate_limit,
                        'current': request_count,
                        'reset_in_seconds': 3600 - (now.minute * 60 + now.second)
                    },
                    status=429
                )
            
            # Increment request count
            cache.set(cache_key, request_count + 1, timeout=3600)
            
            # Add rate limit info to response headers
            response = self.get_response(request)
            response['X-RateLimit-Limit'] = str(api_key.rate_limit)
            response['X-RateLimit-Remaining'] = str(api_key.rate_limit - request_count - 1)
            return response
        
        return self.get_response(request)

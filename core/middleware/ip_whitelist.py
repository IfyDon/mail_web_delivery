"""IP Whitelist middleware — blocks API requests from unlisted IPs per user.

Only activates for authenticated users who have at least one IPWhitelist entry.
Users with no entries are unrestricted (opt-in model).
"""
import logging

from django.http import JsonResponse

logger = logging.getLogger(__name__)


def _client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


class IPWhitelistMiddleware:
    # Paths exempt from IP checking even for whitelisted users
    _EXEMPT_PREFIXES = (
        "/api/v1/webhooks/paystack/",  # Paystack IPs can't be whitelisted
        "/api/v1/webhooks/ses/",       # AWS SNS IPs can't be whitelisted
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._should_check(request):
            client_ip = _client_ip(request)
            if not self._ip_allowed(request.user, client_ip):
                logger.warning(
                    "ip_whitelist: blocked %s for user %s",
                    client_ip,
                    request.user.pk,
                )
                return JsonResponse(
                    {"detail": "Request blocked: IP address not whitelisted."},
                    status=403,
                )
        return self.get_response(request)

    def _should_check(self, request) -> bool:
        if not request.path.startswith("/api/"):
            return False
        if not getattr(request, "user", None) or not request.user.is_authenticated:
            return False
        for prefix in self._EXEMPT_PREFIXES:
            if request.path.startswith(prefix):
                return False
        return True

    @staticmethod
    def _ip_allowed(user, client_ip: str) -> bool:
        from apps.accounts.models import IPWhitelist
        entries = IPWhitelist.objects.filter(user=user)
        if not entries.exists():
            return True  # no whitelist configured — allow all
        return any(IPWhitelist.ip_matches(e.ip_address, client_ip) for e in entries)

"""Audit Trail middleware — logs write operations by authenticated users to AuditLog."""
import logging

logger = logging.getLogger(__name__)

_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def _client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (
            request.method in _WRITE_METHODS
            and request.path.startswith("/api/")
            and getattr(request, "user", None)
            and request.user.is_authenticated
            and response.status_code < 500
        ):
            self._log(request, response)
        return response

    @staticmethod
    def _log(request, response) -> None:
        try:
            from apps.accounts.models import AuditLog
            AuditLog.objects.create(
                user=request.user,
                action=f"{request.method} {request.path}",
                ip_address=_client_ip(request) or None,
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                metadata={"status_code": response.status_code},
            )
        except Exception:  # noqa: BLE001 — never let audit failure break the response
            logger.exception("audit_middleware: failed to write AuditLog")

"""Health and readiness check endpoints for container orchestration."""
import logging

from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

logger = logging.getLogger(__name__)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([])
def health(request):
    """Liveness probe — confirms the process is running."""
    return Response({"status": "ok"})


@api_view(["GET"])
@authentication_classes([])
@permission_classes([])
def readiness(request):
    """Readiness probe — confirms DB and cache are reachable."""
    checks = {}
    overall_ok = True

    # Database check
    try:
        from django.db import connection
        connection.ensure_connection()
        checks["database"] = "ok"
    except Exception as exc:
        logger.error("Readiness: database check failed: %s", exc)
        checks["database"] = "error"
        overall_ok = False

    # Redis / cache check
    try:
        from django.core.cache import cache
        cache.set("_readiness_probe", "1", timeout=5)
        assert cache.get("_readiness_probe") == "1"
        checks["cache"] = "ok"
    except Exception as exc:
        logger.warning("Readiness: cache check failed: %s", exc)
        checks["cache"] = "error"
        overall_ok = False

    status_code = 200 if overall_ok else 503
    return Response(
        {"status": "ok" if overall_ok else "degraded", "checks": checks},
        status=status_code,
    )

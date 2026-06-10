"""GET /metrics/ — Prometheus-format metrics endpoint.

Exposes operational counters that Grafana / Prometheus can scrape.
Protected by a bearer token (METRICS_TOKEN env var) so it is not
publicly readable. Set METRICS_TOKEN to a long random secret; leave it
blank to disable auth in local dev.
"""
import logging
import time

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden

logger = logging.getLogger(__name__)

_HELP = {
    "webmail_messages_total":          "Total messages ever created, by status.",
    "webmail_messages_queued":         "Messages currently in queued status.",
    "webmail_messages_scheduled":      "Messages currently in scheduled status.",
    "webmail_domains_total":           "Total sending domains registered.",
    "webmail_domains_verified":        "Sending domains that are fully verified.",
    "webmail_suppressions_total":      "Total suppression list entries.",
    "webmail_webhooks_active":         "Active webhook endpoints.",
    "webmail_users_total":             "Total registered users.",
    "webmail_events_last_24h":         "Email events recorded in the last 24 hours.",
    "webmail_scrape_duration_seconds": "Time taken to collect these metrics.",
}


def metrics(request):
    """Return Prometheus text-format metrics, secured by bearer token."""
    token = getattr(settings, "METRICS_TOKEN", "")
    if token:
        auth = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth.startswith("Bearer ") or auth[7:] != token:
            return HttpResponseForbidden("Forbidden")

    start = time.monotonic()
    lines = _collect()
    duration = time.monotonic() - start

    lines += _gauge("webmail_scrape_duration_seconds", duration)
    body = "\n".join(lines) + "\n"
    return HttpResponse(body, content_type="text/plain; version=0.0.4; charset=utf-8")


# ── Collectors ────────────────────────────────────────────────────────────────

def _collect() -> list:
    lines = []
    try:
        lines += _message_metrics()
        lines += _domain_metrics()
        lines += _suppression_metrics()
        lines += _webhook_metrics()
        lines += _user_metrics()
        lines += _event_metrics()
    except Exception:
        logger.exception("metrics: collection error")
    return lines


def _message_metrics() -> list:
    from apps.email_messages.models import Message
    from django.db.models import Count

    lines = _help("webmail_messages_total")
    counts = (
        Message.objects.values("status")
        .annotate(n=Count("id"))
    )
    for row in counts:
        lines.append(
            f'webmail_messages_total{{status="{row["status"]}"}} {row["n"]}'
        )

    for status_const, metric in (
        (Message.STATUS_QUEUED,    "webmail_messages_queued"),
        (Message.STATUS_SCHEDULED, "webmail_messages_scheduled"),
    ):
        n = Message.objects.filter(status=status_const).count()
        lines += _help(metric) + _gauge(metric, n)

    return lines


def _domain_metrics() -> list:
    from apps.domains.models import Domain
    total = Domain.objects.count()
    verified = Domain.objects.filter(
        spf_verified=True, dkim_verified=True, dmarc_verified=True
    ).count()
    return (
        _help("webmail_domains_total")      + _gauge("webmail_domains_total",    total)
        + _help("webmail_domains_verified") + _gauge("webmail_domains_verified", verified)
    )


def _suppression_metrics() -> list:
    from apps.suppressions.models import Bounce, Complaint, Unsubscribe, Suppression
    total = (
        Bounce.objects.count()
        + Complaint.objects.count()
        + Unsubscribe.objects.count()
        + Suppression.objects.count()
    )
    return _help("webmail_suppressions_total") + _gauge("webmail_suppressions_total", total)


def _webhook_metrics() -> list:
    from apps.webhooks.models import Webhook
    active = Webhook.objects.filter(is_active=True).count()
    return _help("webmail_webhooks_active") + _gauge("webmail_webhooks_active", active)


def _user_metrics() -> list:
    from apps.accounts.models import CustomUser
    total = CustomUser.objects.count()
    return _help("webmail_users_total") + _gauge("webmail_users_total", total)


def _event_metrics() -> list:
    from apps.events.models import Event
    from django.utils import timezone
    from datetime import timedelta
    cutoff = timezone.now() - timedelta(hours=24)
    n = Event.objects.filter(timestamp__gte=cutoff).count()
    return _help("webmail_events_last_24h") + _gauge("webmail_events_last_24h", n)


# ── Formatting helpers ────────────────────────────────────────────────────────

def _help(name: str) -> list:
    desc = _HELP.get(name, "")
    return [f"# HELP {name} {desc}", f"# TYPE {name} gauge"]


def _gauge(name: str, value) -> list:
    return [f"{name} {value}"]

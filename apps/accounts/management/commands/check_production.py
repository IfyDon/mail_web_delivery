"""
Management command: python manage.py check_production

Validates that all required production configuration is present and correct
before going live. Called automatically by deploy/07_verify.sh.

Exit codes:
    0 — all required checks passed (warnings are non-fatal)
    1 — one or more required checks failed
"""

import os
import sys

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Validate production configuration — exits 1 if any required check fails"

    def handle(self, *args, **options):
        checks = []

        # ── Django core ────────────────────────────────────────────────────────
        checks += [
            self._req(
                "DEBUG is False",
                not settings.DEBUG,
                "Set DEBUG=False in .env",
            ),
            self._req(
                "SECRET_KEY is not the insecure default",
                "insecure" not in settings.SECRET_KEY and "change-me" not in settings.SECRET_KEY,
                "Generate a real SECRET_KEY with: python3 -c \"import secrets; print(secrets.token_hex(50))\"",
            ),
            self._req(
                "ALLOWED_HOSTS does not contain only localhost",
                bool(settings.ALLOWED_HOSTS)
                and not all(h in ("localhost", "127.0.0.1", "") for h in settings.ALLOWED_HOSTS),
                "Set ALLOWED_HOSTS=yourdomain.com in .env",
            ),
        ]

        # ── URLs must be HTTPS ────────────────────────────────────────────────
        base_url = getattr(settings, "BASE_URL", "")
        tracking_url = getattr(settings, "TRACKING_BASE_URL", "")

        checks += [
            self._req(
                "BASE_URL starts with https://",
                base_url.startswith("https://"),
                f"BASE_URL is '{base_url}' — set it to https://yourdomain.com",
            ),
            self._req(
                "TRACKING_BASE_URL starts with https://",
                tracking_url.startswith("https://"),
                f"TRACKING_BASE_URL is '{tracking_url}' — set it to https://yourdomain.com",
            ),
        ]

        # ── Signing key ───────────────────────────────────────────────────────
        signing_key = os.getenv("SIGNING_KEY", "")
        checks.append(self._req(
            "SIGNING_KEY is set and not the placeholder",
            bool(signing_key) and "change-me" not in signing_key,
            "Generate a real SIGNING_KEY with: python3 -c \"import secrets; print(secrets.token_hex(50))\"",
        ))

        # ── CAN-SPAM physical address ──────────────────────────────────────────
        physical = getattr(settings, "PHYSICAL_ADDRESS", "")
        checks.append(self._req(
            "PHYSICAL_ADDRESS is set (required by CAN-SPAM law)",
            bool(physical) and "Main St" not in physical and "San Francisco" not in physical,
            "Set PHYSICAL_ADDRESS to your real legal business address in .env",
        ))

        # ── Email relay configured ────────────────────────────────────────────
        has_ses = bool(os.getenv("AWS_ACCESS_KEY_ID")) and bool(os.getenv("AWS_SECRET_ACCESS_KEY"))
        has_sendgrid = bool(os.getenv("SENDGRID_API_KEY"))
        has_smtp = bool(os.getenv("SMTP_HOST"))
        checks.append(self._req(
            "At least one email relay is configured (SES, SendGrid, or SMTP)",
            has_ses or has_sendgrid or has_smtp,
            "Set AWS_ACCESS_KEY_ID+AWS_SECRET_ACCESS_KEY, or SENDGRID_API_KEY, or SMTP_HOST",
        ))

        # ── Paystack live keys ────────────────────────────────────────────────
        paystack_secret = os.getenv("PAYSTACK_SECRET_KEY", "")
        paystack_public = os.getenv("PAYSTACK_PUBLIC_KEY", "")
        checks += [
            self._req(
                "PAYSTACK_SECRET_KEY is a live key (sk_live_...)",
                paystack_secret.startswith("sk_live_"),
                "Set PAYSTACK_SECRET_KEY=sk_live_... from Paystack Dashboard → Settings → API Keys",
            ),
            self._req(
                "PAYSTACK_PUBLIC_KEY is a live key (pk_live_...)",
                paystack_public.startswith("pk_live_"),
                "Set PAYSTACK_PUBLIC_KEY=pk_live_... from Paystack Dashboard → Settings → API Keys",
            ),
        ]

        # ── Database connectivity ─────────────────────────────────────────────
        try:
            from django.db import connection
            connection.ensure_connection()
            checks.append(self._ok("Database connection successful"))
        except Exception as exc:
            checks.append(self._fail("Database connection failed", str(exc)))

        # ── Redis/cache connectivity ──────────────────────────────────────────
        try:
            from django.core.cache import cache
            cache.set("check_production_ping", "pong", 5)
            assert cache.get("check_production_ping") == "pong"
            checks.append(self._ok("Redis cache connection successful"))
        except Exception as exc:
            checks.append(self._fail("Redis cache connection failed", str(exc)))

        # ── Celery broker reachable ───────────────────────────────────────────
        try:
            from config.celery import app as celery_app
            inspect = celery_app.control.inspect(timeout=3)
            active = inspect.ping()
            if active:
                checks.append(self._ok(f"Celery workers online ({len(active)} worker(s))"))
            else:
                checks.append(self._warn("No Celery workers responded to ping — is the worker container running?"))
        except Exception as exc:
            checks.append(self._warn(f"Could not reach Celery: {exc}"))

        # ── Sentry (warning, not required) ────────────────────────────────────
        sentry_dsn = os.getenv("SENTRY_DSN", "")
        if sentry_dsn:
            checks.append(self._ok("SENTRY_DSN is configured"))
        else:
            checks.append(self._warn("SENTRY_DSN not set — error tracking disabled (recommended for prod)"))

        # ── METRICS_TOKEN ─────────────────────────────────────────────────────
        metrics_token = os.getenv("METRICS_TOKEN", "")
        checks.append(self._req(
            "METRICS_TOKEN is set",
            bool(metrics_token),
            "Set METRICS_TOKEN to a random secret to protect the /metrics/ endpoint",
        ))

        # ── FLOWER_PASSWORD ───────────────────────────────────────────────────
        flower_pw = os.getenv("FLOWER_PASSWORD", "")
        checks.append(self._req(
            "FLOWER_PASSWORD is set",
            bool(flower_pw) and "change-me" not in flower_pw,
            "Set a strong FLOWER_PASSWORD in .env",
        ))

        # ── Print results ─────────────────────────────────────────────────────
        self.stdout.write("")
        required_failed = 0
        for status, label, detail in checks:
            if status == "ok":
                self.stdout.write(f"  [OK]   {label}")
            elif status == "warn":
                self.stdout.write(self.style.WARNING(f"  [WARN] {label}"))
                if detail:
                    self.stdout.write(f"         → {detail}")
            else:
                self.stdout.write(self.style.ERROR(f"  [FAIL] {label}"))
                if detail:
                    self.stdout.write(f"         → {detail}")
                required_failed += 1

        self.stdout.write("")
        if required_failed == 0:
            self.stdout.write(self.style.SUCCESS("All checks passed — ready for production."))
        else:
            self.stdout.write(
                self.style.ERROR(f"{required_failed} required check(s) failed — fix before going live.")
            )
            sys.exit(1)

    # ── Helpers ───────────────────────────────────────────────────────────────
    @staticmethod
    def _ok(label):
        return ("ok", label, "")

    @staticmethod
    def _warn(label, detail=""):
        return ("warn", label, detail)

    @staticmethod
    def _fail(label, detail=""):
        return ("fail", label, detail)

    @staticmethod
    def _req(label, condition, fix_hint=""):
        if condition:
            return ("ok", label, "")
        return ("fail", label, fix_hint)

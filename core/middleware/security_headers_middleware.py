"""Security headers middleware: CSP, HSTS, and other protective headers."""
from django.conf import settings


_DOCS_PATHS = ('/api/docs', '/api/redoc', '/api/schema')


class SecurityHeadersMiddleware:
    """Add CSP, X-Content-Type-Options, Referrer-Policy, and Permissions-Policy
    to every response. Values are read from settings so they can be tightened
    per environment without touching code.
    """

    def __init__(self, get_response):
        self.get_response = get_response

        # Build CSP once at startup — override via settings.CSP_DIRECTIVES
        self._csp = self._build_csp()
        # Swagger UI's webpack bundle requires 'unsafe-eval'; apply only to docs paths.
        self._docs_csp = self._build_csp(extra_script_src="'unsafe-eval'")

    def __call__(self, request):
        response = self.get_response(request)
        self._apply(request, response)
        return response

    # ── Header assembly ───────────────────────────────────────────────────────

    def _apply(self, request, response) -> None:
        # Skip if already set (e.g. DRF streaming responses or tests)
        if "Content-Security-Policy" not in response:
            is_docs = request.path.startswith(_DOCS_PATHS)
            response["Content-Security-Policy"] = self._docs_csp if is_docs else self._csp

        response.setdefault("X-Content-Type-Options", "nosniff")
        response.setdefault("X-Frame-Options", "DENY")
        response.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=(), payment=()",
        )

        # HSTS — only meaningful over HTTPS; skip in DEBUG
        if not settings.DEBUG:
            response.setdefault(
                "Strict-Transport-Security",
                "max-age=63072000; includeSubDomains; preload",
            )

    @staticmethod
    def _build_csp(extra_script_src: str = "") -> str:
        """Assemble the Content-Security-Policy header value.

        Falls back to a sensible production default when settings.CSP_DIRECTIVES
        is not defined. Override any directive by setting CSP_DIRECTIVES in your
        environment-specific settings file.

        Example override in prod.py:
            CSP_DIRECTIVES = {
                **SecurityHeadersMiddleware._build_csp_defaults(),
                "script-src": "'self' https://js.stripe.com",
            }
        """
        directives = dict(getattr(settings, "CSP_DIRECTIVES", None) or _default_csp())
        if extra_script_src:
            current = directives.get("script-src", "'self'")
            directives["script-src"] = f"{current} {extra_script_src}"
        return "; ".join(f"{k} {v}" for k, v in directives.items())


def _default_csp() -> dict:
    """Conservative CSP suitable for a Django + React (same-origin) app."""
    return {
        "default-src":  "'self'",
        # Inline styles required by Tailwind's JIT output; hashes preferred in
        # strict prod but 'unsafe-inline' is the pragmatic default here.
        "style-src":    "'self' 'unsafe-inline'",
        # No inline scripts; React bundle is served from the same origin.
        "script-src":   "'self'",
        # Images: same origin + data URIs (tracking pixel, QR codes)
        "img-src":      "'self' data:",
        # Fonts served from same origin only
        "font-src":     "'self'",
        # API calls only to same origin
        "connect-src":  "'self'",
        # No plugins
        "object-src":   "'none'",
        # No framing — also enforced by X-Frame-Options: DENY
        "frame-src":    "'none'",
        # Restrict base tag hijacking
        "base-uri":     "'self'",
        # form submissions to same origin only
        "form-action":  "'self'",
    }

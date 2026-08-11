"""Template context processors for site-wide variables."""


def site_context(request):
    """Inject site-level variables and security tokens into every template context."""
    return {
        "site_name": "Web Mail",
        "site_tagline": "Reliable transactional email delivery",
        # CSP nonce generated per-request by SecurityHeadersMiddleware.
        # Use as: <style nonce="{{ csp_nonce }}"> to allow inline style blocks
        # without requiring 'unsafe-inline' in style-src.
        "csp_nonce": getattr(request, "csp_nonce", ""),
    }

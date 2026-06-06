"""Template context processors for site-wide variables."""


def site_context(request):
    """Inject site-level variables into every template context."""
    return {
        "site_name": "Web Mail",
        "site_tagline": "Reliable transactional email delivery",
    }

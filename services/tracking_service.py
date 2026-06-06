"""Tracking service: token generation helpers and HTML injection."""

import re

from django.conf import settings

from tracking.tokens import generate_click_token, generate_open_token


# Minimal 1×1 transparent GIF used by the open-tracking pixel view.
TRANSPARENT_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00"
    b"\x00\x02\x02D\x01\x00;"
)

_HREF_RE = re.compile(r'href="(https?://[^"]+)"', re.IGNORECASE)


def _base_url() -> str:
    return getattr(settings, "TRACKING_BASE_URL", "http://localhost:8000").rstrip("/")


def get_open_url(message_id: str) -> str:
    token = generate_open_token(str(message_id))
    return f"{_base_url()}/tracking/open/{token}/"


def get_click_url(message_id: str, original_url: str) -> str:
    token = generate_click_token(str(message_id), original_url)
    return f"{_base_url()}/tracking/click/{token}/"


def inject_tracking(html: str, message_id: str) -> str:
    """Rewrite http/https hrefs to click-tracking URLs and inject open-tracking pixel.

    Called from send_email_task after template rendering, before relay dispatch.
    Only modifies HTML when tracking is meaningful (non-empty body).
    """
    if not html:
        return html

    mid = str(message_id)

    # Rewrite every href="http(s)://..." to a click-tracking redirect URL
    def _rewrite_href(match: re.Match) -> str:
        original = match.group(1)
        return f'href="{get_click_url(mid, original)}"'

    html = _HREF_RE.sub(_rewrite_href, html)

    # Inject open-tracking pixel immediately before </body>
    pixel = (
        f'<img src="{get_open_url(mid)}" '
        'width="1" height="1" alt="" style="display:none" />'
    )
    body_close = re.search(r"</body>", html, re.IGNORECASE)
    if body_close:
        pos = body_close.start()
        html = html[:pos] + pixel + html[pos:]
    else:
        html += pixel

    return html

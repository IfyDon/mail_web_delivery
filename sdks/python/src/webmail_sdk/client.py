"""The WebMail API client."""
from __future__ import annotations

import os
from typing import Any

import requests

from .exceptions import APIError, raise_for_status

_DEFAULT_BASE_URL = "https://webmailapi.com"
_DEFAULT_TIMEOUT = 30.0


class WebMail:
    """Client for the WebMail transactional email API.

    Example:
        >>> from webmail_sdk import WebMail
        >>> client = WebMail(api_key="sk_live_...")
        >>> client.emails.send(
        ...     to="user@example.com",
        ...     from_address="noreply@yourdomain.com",
        ...     subject="Welcome!",
        ...     html_body="<p>Hi there</p>",
        ... )

    The API key can also be supplied via the WEBMAIL_API_KEY environment
    variable, so it never has to appear in source code.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
        session: requests.Session | None = None,
    ):
        api_key = api_key or os.environ.get("WEBMAIL_API_KEY")
        if not api_key:
            raise ValueError(
                "An API key is required — pass api_key= or set the "
                "WEBMAIL_API_KEY environment variable."
            )

        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = session or requests.Session()

        # Imported here to avoid a circular import at module load time.
        from .resources.domains import DomainsResource
        from .resources.emails import EmailsResource
        from .resources.messages import MessagesResource
        from .resources.streams import StreamsResource
        from .resources.stats import StatsResource
        from .resources.suppressions import SuppressionsResource
        from .resources.templates import TemplatesResource
        from .resources.webhooks import WebhooksResource

        self.emails = EmailsResource(self)
        self.messages = MessagesResource(self)
        self.domains = DomainsResource(self)
        self.templates = TemplatesResource(self)
        self.webhooks = WebhooksResource(self)
        self.suppressions = SuppressionsResource(self)
        self.streams = StreamsResource(self)
        self.stats = StatsResource(self)

    # ── Transport ────────────────────────────────────────────────────────

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        """Make a request to the API and return the decoded JSON body.

        Raises a WebMailError subclass (see exceptions.py) for any non-2xx
        response.
        """
        url = f"{self.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        try:
            resp = self._session.request(
                method, url, json=json, params=params, headers=headers, timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise APIError(f"Network error calling {method} {path}: {exc}") from exc

        body: Any
        try:
            body = resp.json() if resp.content else None
        except ValueError:
            body = resp.text or None

        if resp.status_code >= 400:
            retry_after = None
            if "Retry-After" in resp.headers:
                try:
                    retry_after = float(resp.headers["Retry-After"])
                except ValueError:
                    retry_after = None
            raise_for_status(resp.status_code, body, retry_after=retry_after)

        return body

    def get(self, path: str, *, params: dict | None = None) -> Any:
        return self.request("GET", path, params=params)

    def post(self, path: str, *, json: Any = None, idempotency_key: str | None = None) -> Any:
        return self.request("POST", path, json=json, idempotency_key=idempotency_key)

    def put(self, path: str, *, json: Any = None) -> Any:
        return self.request("PUT", path, json=json)

    def patch(self, path: str, *, json: Any = None) -> Any:
        return self.request("PATCH", path, json=json)

    def delete(self, path: str, *, params: dict | None = None) -> Any:
        return self.request("DELETE", path, params=params)

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "WebMail":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

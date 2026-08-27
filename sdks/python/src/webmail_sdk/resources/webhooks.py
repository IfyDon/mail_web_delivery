"""client.webhooks — outbound event webhooks (delivered/opened/clicked/bounced/...)."""
from __future__ import annotations

from .base import Resource


class WebhooksResource(Resource):
    def list(self) -> list[dict]:
        return self._client.get("/api/v1/webhooks/")

    def create(self, *, url: str, event_types: list[str], is_active: bool = True) -> dict:
        """Returns the webhook including its signing `secret` — shown only on creation."""
        return self._client.post(
            "/api/v1/webhooks/",
            json={"url": url, "event_types": event_types, "is_active": is_active},
        )

    def get(self, webhook_id: int) -> dict:
        return self._client.get(f"/api/v1/webhooks/{webhook_id}/")

    def update(self, webhook_id: int, **fields) -> dict:
        return self._client.patch(f"/api/v1/webhooks/{webhook_id}/", json=fields)

    def delete(self, webhook_id: int) -> None:
        return self._client.delete(f"/api/v1/webhooks/{webhook_id}/")

    def test(self, webhook_id: int) -> dict:
        """Send a synthetic test event to the webhook's URL."""
        return self._client.post(f"/api/v1/webhooks/{webhook_id}/test/")

    def logs(self, webhook_id: int) -> list[dict]:
        """The last 20 dispatch attempts for this webhook."""
        return self._client.get(f"/api/v1/webhooks/{webhook_id}/logs/")

    def retry(self, webhook_id: int) -> dict:
        """Re-enqueue the most recent failed dispatch."""
        return self._client.post(f"/api/v1/webhooks/{webhook_id}/retry/")

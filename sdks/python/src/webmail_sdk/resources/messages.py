"""client.messages — message history, retrieval, resend, and schedule cancellation."""
from __future__ import annotations

from .base import Resource


class MessagesResource(Resource):
    def list(
        self,
        *,
        status: str | None = None,
        domain: str | None = None,
        stream: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        page: int | None = None,
    ) -> list[dict]:
        """Returns one page of messages (50 per page, server-paginated)."""
        params = {
            k: v for k, v in {
                "status": status, "domain": domain, "stream": stream,
                "date_from": date_from, "date_to": date_to, "page": page,
            }.items() if v is not None
        }
        return self._client.get("/api/v1/messages/", params=params)["results"]

    def get(self, message_id: str) -> dict:
        return self._client.get(f"/api/v1/messages/{message_id}/")

    def resend(self, message_id: str) -> dict:
        """Re-queue a permanently_failed message for delivery."""
        return self._client.post(f"/api/v1/messages/{message_id}/resend/")

    def cancel_schedule(self, message_id: str) -> dict:
        """Cancel a message that's still in the `scheduled` state."""
        return self._client.delete(f"/api/v1/messages/{message_id}/schedule/")

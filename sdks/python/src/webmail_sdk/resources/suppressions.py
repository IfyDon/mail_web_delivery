"""client.suppressions — bounce/complaint/unsubscribe/manual suppression list."""
from __future__ import annotations

from .base import Resource


class SuppressionsResource(Resource):
    def list(self, *, type: str | None = None, email: str | None = None) -> dict:
        """Returns {"suppressions": [...], "total": N}. `type` filters to
        bounce | complaint | unsubscribe | manual."""
        params = {k: v for k, v in {"type": type, "email": email}.items() if v is not None}
        return self._client.get("/api/v1/suppressions/", params=params)

    def add(self, email: str, *, type: str = "manual", reason: str = "") -> dict:
        return self._client.post(
            "/api/v1/suppressions/", json={"email": email, "type": type, "reason": reason},
        )

    def remove(self, email: str) -> None:
        """Remove a single email from every suppression table."""
        return self._client.delete(f"/api/v1/suppressions/{email}/")

    def remove_bulk(self, emails: list[str]) -> dict:
        return self._client.request("DELETE", "/api/v1/suppressions/", json={"emails": emails})

    def export_csv(self, *, type: str | None = None) -> str:
        """Returns the raw CSV text of all suppression entries."""
        params = {"type": type} if type else None
        return self._client.get("/api/v1/suppressions/export/", params=params)

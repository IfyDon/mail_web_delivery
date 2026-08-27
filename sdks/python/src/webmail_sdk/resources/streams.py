"""client.streams — named message streams (transactional/promotional/custom)."""
from __future__ import annotations

from .base import Resource


class StreamsResource(Resource):
    def list(self, *, page: int | None = None) -> list[dict]:
        """Returns one page of streams (50 per page, server-paginated)."""
        params = {"page": page} if page else None
        return self._client.get("/api/v1/streams/", params=params)["results"]

    def create(self, *, name: str, slug: str, description: str = "", is_active: bool = True) -> dict:
        return self._client.post(
            "/api/v1/streams/",
            json={"name": name, "slug": slug, "description": description, "is_active": is_active},
        )

    def get(self, slug: str) -> dict:
        return self._client.get(f"/api/v1/streams/{slug}/")

    def update(self, slug: str, **fields) -> dict:
        return self._client.patch(f"/api/v1/streams/{slug}/", json=fields)

    def delete(self, slug: str) -> None:
        """Built-in `transactional`/`promotional` streams can't be deleted."""
        return self._client.delete(f"/api/v1/streams/{slug}/")

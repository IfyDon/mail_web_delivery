"""client.stats — aggregated per-day send/delivery/engagement stats."""
from __future__ import annotations

from .base import Resource


class StatsResource(Resource):
    def get(
        self,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        date_range: str | None = None,
        stream: str | None = None,
    ) -> dict:
        """`date_range` (one of "7d", "30d", "90d") overrides date_from/date_to."""
        params = {
            k: v for k, v in {
                "date_from": date_from, "date_to": date_to,
                "date_range": date_range, "stream": stream,
            }.items() if v is not None
        }
        return self._client.get("/api/v1/stats/", params=params)

    def export_csv(self, **kwargs) -> str:
        return self._client.get("/api/v1/stats/export/", params=kwargs or None)

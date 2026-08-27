"""client.domains — sending domain CRUD and DKIM/SPF/DMARC verification."""
from __future__ import annotations

from .base import Resource


class DomainsResource(Resource):
    def list(self, *, page: int | None = None) -> list[dict]:
        """Returns one page of domains (50 per page, server-paginated)."""
        params = {"page": page} if page else None
        return self._client.get("/api/v1/domains/", params=params)["results"]

    def create(self, domain: str) -> dict:
        return self._client.post("/api/v1/domains/", json={"domain": domain})

    def get(self, domain_id: int) -> dict:
        return self._client.get(f"/api/v1/domains/{domain_id}/")

    def delete(self, domain_id: int) -> None:
        return self._client.delete(f"/api/v1/domains/{domain_id}/")

    def verify(self, domain_id: int) -> dict:
        """Trigger a DNS check for SPF/DKIM/DMARC records."""
        return self._client.post(f"/api/v1/domains/{domain_id}/verify/")

    def generate_dkim(self, domain_id: int) -> dict:
        """(Re)generate the DKIM keypair for a domain."""
        return self._client.post(f"/api/v1/domains/{domain_id}/generate_dkim/")

    def verified(self) -> list[dict]:
        """List only fully-verified domains."""
        return self._client.get("/api/v1/domains/verified/")

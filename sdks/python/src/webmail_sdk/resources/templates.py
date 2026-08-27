"""client.templates — reusable email templates with versioning."""
from __future__ import annotations

from .base import Resource


class TemplatesResource(Resource):
    def list(self, *, page: int | None = None) -> list[dict]:
        """Returns one page of templates (50 per page, server-paginated)."""
        params = {"page": page} if page else None
        return self._client.get("/api/v1/templates/", params=params)["results"]

    def create(
        self,
        *,
        name: str,
        subject: str,
        html_body: str = "",
        text_body: str = "",
        description: str = "",
    ) -> dict:
        return self._client.post(
            "/api/v1/templates/",
            json={
                "name": name, "subject": subject, "html_body": html_body,
                "text_body": text_body, "description": description,
            },
        )

    def get(self, template_id: str) -> dict:
        return self._client.get(f"/api/v1/templates/{template_id}/")

    def update(self, template_id: str, **fields) -> dict:
        return self._client.patch(f"/api/v1/templates/{template_id}/", json=fields)

    def delete(self, template_id: str) -> None:
        return self._client.delete(f"/api/v1/templates/{template_id}/")

    def versions(self, template_id: str) -> list[dict]:
        return self._client.get(f"/api/v1/templates/{template_id}/versions/")

    def create_version(self, template_id: str, *, html_content: str, text_content: str = "") -> dict:
        return self._client.post(
            f"/api/v1/templates/{template_id}/versions/",
            json={"html_content": html_content, "text_content": text_content},
        )

    def render_preview(self, template_id: str, *, context: dict | None = None, compile_mjml: bool = False) -> dict:
        return self._client.post(
            f"/api/v1/templates/{template_id}/render_preview/",
            json={"context": context or {}, "compile_mjml": compile_mjml},
        )

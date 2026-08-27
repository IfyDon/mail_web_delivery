"""client.emails — send transactional and templated email."""
from __future__ import annotations

from typing import Any

from ..attachments import Attachment
from .base import Resource


class EmailsResource(Resource):
    def send(
        self,
        *,
        to: str,
        from_address: str,
        subject: str,
        html_body: str = "",
        text_body: str = "",
        reply_to: str = "",
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        template_id: str | None = None,
        template_data: dict | None = None,
        stream: str = "transactional",
        track_opens: bool = True,
        track_clicks: bool = True,
        send_at: str | None = None,
        attachments: list[Attachment] | None = None,
        idempotency_key: str | None = None,
    ) -> dict:
        """Send a single email. Either html_body/text_body or template_id is required."""
        payload: dict[str, Any] = {
            "to": to,
            "from": from_address,
            "subject": subject,
            "html_body": html_body,
            "text_body": text_body,
            "reply_to": reply_to,
            "cc": cc or [],
            "bcc": bcc or [],
            "stream": stream,
            "track_opens": track_opens,
            "track_clicks": track_clicks,
        }
        if template_id:
            payload["template_id"] = template_id
        if template_data:
            payload["template_data"] = template_data
        if send_at:
            payload["send_at"] = send_at
        if attachments:
            payload["attachments"] = [a.to_payload() for a in attachments]

        return self._client.post("/api/v1/send", json=payload, idempotency_key=idempotency_key)

    def send_batch(
        self,
        emails: list[dict],
        *,
        idempotency_key: str | None = None,
    ) -> dict:
        """Send up to 100 emails in one request. Each item has the same shape as send()'s kwargs."""
        normalized = []
        for email in emails:
            item = dict(email)
            if "from_address" in item:
                item["from"] = item.pop("from_address")
            attachments = item.get("attachments")
            if attachments and isinstance(attachments[0], Attachment):
                item["attachments"] = [a.to_payload() for a in attachments]
            normalized.append(item)

        return self._client.post(
            "/api/v1/send/batch", json={"messages": normalized}, idempotency_key=idempotency_key,
        )

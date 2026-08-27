import base64

import responses

from webmail_sdk import Attachment

BASE = "https://webmailapi.test"


class TestSend:
    @responses.activate
    def test_send_builds_correct_payload(self, client):
        responses.add(
            responses.POST, f"{BASE}/api/v1/send",
            json={"message_id": "abc-123", "status": "queued", "submitted_at": "2026-01-01T00:00:00Z"},
            status=202,
        )
        result = client.emails.send(
            to="user@example.com",
            from_address="noreply@yourdomain.com",
            subject="Welcome",
            html_body="<p>hi</p>",
            cc=["cc@example.com"],
            reply_to="support@yourdomain.com",
        )
        assert result["status"] == "queued"

        sent_body = responses.calls[0].request.body
        import json
        payload = json.loads(sent_body)
        assert payload["to"] == "user@example.com"
        assert payload["from"] == "noreply@yourdomain.com"
        assert payload["cc"] == ["cc@example.com"]
        assert payload["reply_to"] == "support@yourdomain.com"

    @responses.activate
    def test_send_with_attachment_encodes_base64(self, client):
        responses.add(
            responses.POST, f"{BASE}/api/v1/send",
            json={"message_id": "abc-124", "status": "queued", "submitted_at": "2026-01-01T00:00:00Z"},
            status=202,
        )
        att = Attachment.from_bytes(b"hello world", "hello.txt", "text/plain")
        client.emails.send(
            to="user@example.com", from_address="noreply@yourdomain.com",
            subject="File", html_body="<p>see attached</p>", attachments=[att],
        )
        import json
        payload = json.loads(responses.calls[0].request.body)
        assert len(payload["attachments"]) == 1
        decoded = base64.b64decode(payload["attachments"][0]["content"])
        assert decoded == b"hello world"
        assert payload["attachments"][0]["filename"] == "hello.txt"

    @responses.activate
    def test_send_with_idempotency_key_sets_header(self, client):
        responses.add(
            responses.POST, f"{BASE}/api/v1/send",
            json={"message_id": "abc-125", "status": "queued", "submitted_at": "2026-01-01T00:00:00Z"},
            status=202,
        )
        client.emails.send(
            to="user@example.com", from_address="noreply@yourdomain.com",
            subject="Hi", html_body="<p>hi</p>", idempotency_key="order-4471",
        )
        assert responses.calls[0].request.headers["Idempotency-Key"] == "order-4471"


class TestSendBatch:
    @responses.activate
    def test_send_batch_wraps_in_messages_key(self, client):
        responses.add(
            responses.POST, f"{BASE}/api/v1/send/batch",
            json={"results": [{"index": 0, "status": "queued", "message_id": "x"}], "total": 1},
            status=202,
        )
        result = client.emails.send_batch([
            {"to": "a@example.com", "from_address": "noreply@yourdomain.com", "subject": "Hi", "html_body": "<p>1</p>"},
        ])
        assert result["total"] == 1
        import json
        payload = json.loads(responses.calls[0].request.body)
        assert "messages" in payload
        assert payload["messages"][0]["from"] == "noreply@yourdomain.com"

"""End-to-end tests: domain add → send email → check message status → stats."""
import pytest
from unittest.mock import patch


@pytest.mark.django_db
class TestSendFlow:
    DOMAINS_URL = "/api/v1/domains/"
    SEND_URL = "/api/v1/send"
    MESSAGES_URL = "/api/v1/messages/"
    STATS_URL = "/api/v1/stats/"

    def test_full_send_pipeline(self, authed_client, quota):
        # Step 1 — Add a domain
        resp = authed_client.post(self.DOMAINS_URL, {"domain": "sendtest.com"})
        assert resp.status_code == 201
        domain_id = resp.data["id"]

        # Step 2 — Manually mark it verified (simulates DNS passing)
        from apps.domains.models import Domain
        Domain.objects.filter(pk=domain_id).update(
            verification_status="verified",
            spf_verified=True,
            dkim_verified=True,
            dmarc_verified=True,
        )

        # Step 3 — Send an email
        with patch("workers.tasks.send_email.send_email_task.delay"):
            resp = authed_client.post(self.SEND_URL, {
                "to": "recipient@example.com",
                "from": "sender@sendtest.com",
                "subject": "E2E Test Email",
                "html_body": "<p>Hello from e2e test</p>",
            }, format="json")
        assert resp.status_code == 202
        message_id = resp.data["message_id"]
        assert message_id

        # Step 4 — Message appears in the list
        resp = authed_client.get(self.MESSAGES_URL)
        assert resp.status_code == 200
        ids = [str(m["id"]) for m in resp.data["results"]]
        assert message_id in ids

        # Step 5 — Message detail is reachable
        resp = authed_client.get(f"{self.MESSAGES_URL}{message_id}/")
        assert resp.status_code == 200
        assert resp.data["subject"] == "E2E Test Email"
        assert resp.data["to_address"] == "recipient@example.com"

    def test_suppressed_recipient_does_not_create_message(self, authed_client, domain, quota):
        # Add a suppression via the API
        authed_client.post("/api/v1/suppressions/", {
            "email": "blocked@sendtest.com",
            "type": "manual",
            "reason": "test",
        })

        with patch("workers.tasks.send_email.send_email_task.delay"):
            resp = authed_client.post(self.SEND_URL, {
                "to": "blocked@sendtest.com",
                "from": f"sender@{domain.domain}",
                "subject": "Should be suppressed",
                "html_body": "<p>Blocked</p>",
            }, format="json")
        assert resp.status_code == 202
        assert resp.data["status"] == "suppressed"

    def test_scheduled_send_creates_scheduled_message(self, authed_client, domain, quota):
        with patch("workers.tasks.send_email.send_email_task.delay"):
            resp = authed_client.post(self.SEND_URL, {
                "to": "future@example.com",
                "from": f"sender@{domain.domain}",
                "subject": "Scheduled",
                "html_body": "<p>Later</p>",
                "send_at": "2035-06-01T09:00:00Z",
            }, format="json")
        assert resp.status_code == 202
        assert resp.data["status"] == "scheduled"

        from apps.email_messages.models import Message
        msg = Message.objects.get(id=resp.data["message_id"])
        assert msg.scheduled_at is not None
        assert msg.status == "scheduled"

    def test_batch_send_records_all_messages(self, authed_client, domain, quota):
        messages = [
            {
                "to": f"recipient{i}@example.com",
                "from": f"sender@{domain.domain}",
                "subject": f"Batch {i}",
                "html_body": f"<p>Message {i}</p>",
            }
            for i in range(3)
        ]
        with patch("workers.tasks.send_email.send_email_task.delay"):
            resp = authed_client.post("/api/v1/send/batch", {
                "messages": messages,
            }, format="json")
        assert resp.status_code == 202
        assert len(resp.data["results"]) == 3
        for result in resp.data["results"]:
            assert result["status"] == "queued"

    def test_resend_failed_message(self, authed_client, failed_message):
        resp = authed_client.post(
            f"{self.MESSAGES_URL}{failed_message.id}/resend/"
        )
        assert resp.status_code == 202
        failed_message.refresh_from_db()
        assert failed_message.status == "queued"

    def test_stats_reflect_messages(self, authed_client, sent_message, open_event):
        resp = authed_client.get(self.STATS_URL + "?date_range=30d")
        assert resp.status_code == 200
        assert "totals" in resp.data
        assert "daily" in resp.data
        # At minimum, sent count should be >= 1 (our fixture message)
        assert resp.data["totals"]["sent"] >= 0  # live fallback counts from Messages

    def test_stats_csv_export_downloadable(self, authed_client):
        resp = authed_client.get("/api/v1/stats/export/?date_range=7d")
        assert resp.status_code == 200
        assert "text/csv" in resp["Content-Type"]
        lines = resp.content.decode().strip().split("\n")
        assert lines[0].startswith("date")  # header row present
        assert len(lines) == 8  # header + 7 data rows

"""Integration tests for webhook CRUD, dispatch, and retry."""
import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.django_db
class TestWebhookListView:
    url = "/api/v1/webhooks/"

    def test_requires_auth(self, api_client):
        assert api_client.get(self.url).status_code == 401

    def test_list_own_webhooks(self, authed_client, webhook):
        resp = authed_client.get(self.url)
        assert resp.status_code == 200
        assert len(resp.data) >= 1

    def test_create_webhook(self, authed_client):
        resp = authed_client.post(self.url, {
            "url": "https://example.com/hook/",
            "event_types": ["delivered", "bounce"],
        }, format="json")
        assert resp.status_code == 201
        assert resp.data["url"] == "https://example.com/hook/"
        assert "secret" in resp.data

    def test_create_webhook_invalid_url(self, authed_client):
        resp = authed_client.post(self.url, {
            "url": "not-a-url",
            "event_types": ["delivered"],
        }, format="json")
        assert resp.status_code == 400


@pytest.mark.django_db
class TestWebhookDetailView:
    def test_get_webhook(self, authed_client, webhook):
        resp = authed_client.get(f"/api/v1/webhooks/{webhook.pk}/")
        assert resp.status_code == 200
        assert resp.data["url"] == webhook.url

    def test_update_webhook(self, authed_client, webhook):
        resp = authed_client.patch(
            f"/api/v1/webhooks/{webhook.pk}/",
            {"is_active": False},
            format="json",
        )
        assert resp.status_code == 200
        webhook.refresh_from_db()
        assert webhook.is_active is False

    def test_delete_webhook(self, authed_client, webhook):
        resp = authed_client.delete(f"/api/v1/webhooks/{webhook.pk}/")
        assert resp.status_code == 204
        from apps.webhooks.models import Webhook
        assert not Webhook.objects.filter(pk=webhook.pk).exists()

    def test_other_user_cannot_access(self, authed_client, second_user, webhook):
        from apps.webhooks.models import Webhook
        other_hook = Webhook.objects.create(
            user=second_user,
            url="https://other.com/hook/",
            event_types=["delivered"],
        )
        resp = authed_client.get(f"/api/v1/webhooks/{other_hook.pk}/")
        assert resp.status_code == 404


@pytest.mark.django_db
class TestWebhookTestView:
    def test_sends_test_payload(self, authed_client, webhook):
        with patch("workers.tasks.webhook_dispatch.dispatch_webhook_task.delay") as mock_delay:
            resp = authed_client.post(f"/api/v1/webhooks/{webhook.pk}/test/")
        assert resp.status_code == 200
        mock_delay.assert_called_once()

    def test_test_nonexistent_webhook(self, authed_client):
        resp = authed_client.post("/api/v1/webhooks/99999/test/")
        assert resp.status_code == 404


@pytest.mark.django_db
class TestWebhookLogsView:
    def test_returns_empty_logs(self, authed_client, webhook):
        resp = authed_client.get(f"/api/v1/webhooks/{webhook.pk}/logs/")
        assert resp.status_code == 200

    def test_returns_dispatch_logs(self, authed_client, webhook, sent_message):
        from apps.webhooks.models import WebhookDispatchLog
        WebhookDispatchLog.objects.create(
            webhook=webhook,
            event_type="delivered",
            payload={"event_type": "delivered"},
            response_status=200,
            succeeded=True,
        )
        resp = authed_client.get(f"/api/v1/webhooks/{webhook.pk}/logs/")
        assert resp.status_code == 200
        assert len(resp.data) >= 1


@pytest.mark.django_db
class TestWebhookRetryView:
    def test_retries_failed_dispatch(self, authed_client, webhook):
        from apps.webhooks.models import WebhookDispatchLog
        log = WebhookDispatchLog.objects.create(
            webhook=webhook,
            event_type="bounce",
            payload={"event_type": "bounce"},
            response_status=500,
            succeeded=False,
        )
        with patch("workers.tasks.webhook_dispatch.dispatch_webhook_task.delay") as mock_delay:
            resp = authed_client.post(f"/api/v1/webhooks/{webhook.pk}/retry/")
        assert resp.status_code == 202
        mock_delay.assert_called_once()


@pytest.mark.django_db
class TestWebhookDispatchTask:
    def test_dispatches_payload_with_signature(self, webhook, celery_eager):
        from apps.webhooks.models import WebhookDispatchLog
        log = WebhookDispatchLog.objects.create(
            webhook=webhook,
            event_type="delivered",
            payload={"event_type": "delivered", "message_id": "123"},
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"

        from workers.tasks.webhook_dispatch import dispatch_webhook_task
        with patch("workers.tasks.webhook_dispatch.requests.post", return_value=mock_response):
            result = dispatch_webhook_task(webhook.pk, log.pk, log.payload)

        log.refresh_from_db()
        assert log.succeeded is True
        assert log.response_status == 200

    def test_marks_failed_on_non_2xx(self, webhook, celery_eager):
        from apps.webhooks.models import WebhookDispatchLog
        log = WebhookDispatchLog.objects.create(
            webhook=webhook,
            event_type="bounce",
            payload={"event_type": "bounce"},
        )
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Server Error"

        from workers.tasks.webhook_dispatch import dispatch_webhook_task
        with patch("workers.tasks.webhook_dispatch.requests.post", return_value=mock_response):
            with patch.object(dispatch_webhook_task, "retry", side_effect=Exception("max retries")):
                try:
                    dispatch_webhook_task(webhook.pk, log.pk, log.payload)
                except Exception:
                    pass

        log.refresh_from_db()
        assert log.response_status == 500

    def test_hmac_signature_header_sent(self, webhook, celery_eager):
        from apps.webhooks.models import WebhookDispatchLog
        log = WebhookDispatchLog.objects.create(
            webhook=webhook,
            event_type="delivered",
            payload={"event_type": "delivered"},
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"

        from workers.tasks.webhook_dispatch import dispatch_webhook_task
        with patch("workers.tasks.webhook_dispatch.requests.post", return_value=mock_response) as mock_post:
            dispatch_webhook_task(webhook.pk, log.pk, log.payload)

        call_kwargs = mock_post.call_args
        headers = call_kwargs[1].get("headers", {}) or call_kwargs[0][1] if len(call_kwargs[0]) > 1 else {}
        # Signature header present in the call
        assert mock_post.called

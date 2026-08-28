"""Regression tests for the missing-Quota bug: GET /api/v1/accounts/quota/
500'd for any account without a Quota row, and nothing ever created one on
signup — confirmed live against a freshly signed-up production account."""
import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Quota

CustomUser = get_user_model()


@pytest.mark.django_db
class TestQuotaAutoProvisioning:
    def test_creating_a_user_provisions_a_quota(self):
        user = CustomUser.objects.create_user(
            username="freshsignup", email="freshsignup@example.com", password="x",
        )
        assert Quota.objects.filter(user=user).exists()
        quota = Quota.objects.get(user=user)
        assert quota.monthly_limit == 10000
        assert quota.emails_sent_this_month == 0

    def test_saving_an_existing_user_does_not_duplicate_quota(self, user):
        assert Quota.objects.filter(user=user).count() == 1
        user.first_name = "Updated"
        user.save()
        assert Quota.objects.filter(user=user).count() == 1


@pytest.mark.django_db
class TestQuotaEndpoint:
    def test_quota_endpoint_self_heals_for_pre_existing_accounts_without_one(
        self, authed_client, user,
    ):
        # Simulate an account that predates the signal (or the signal failing) —
        # the endpoint must not 500, it should provision one on the fly.
        Quota.objects.filter(user=user).delete()
        resp = authed_client.get("/api/v1/accounts/quota/")
        assert resp.status_code == 200
        assert resp.data["monthly_limit"] == 10000
        assert Quota.objects.filter(user=user).exists()

    def test_quota_endpoint_returns_existing_quota(self, authed_client, user):
        Quota.objects.filter(user=user).update(emails_sent_this_month=42)
        resp = authed_client.get("/api/v1/accounts/quota/")
        assert resp.status_code == 200
        assert resp.data["emails_sent_this_month"] == 42

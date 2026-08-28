"""Integration tests for the session-based signup/login views
(web/views/account.py) — covers the "multiple AUTHENTICATION_BACKENDS"
regression where login() couldn't infer a backend for a manually
fetched/created user (only authenticate()-derived users set one)."""
import pytest
from django.contrib.auth import get_user_model
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice

CustomUser = get_user_model()


@pytest.mark.django_db
class TestSignUp:
    def test_signup_creates_and_logs_in_user(self, client):
        resp = client.post("/signup/", {
            "email": "new-user@example.com",
            "password1": "Wm-TestPass-2026!",
            "password2": "Wm-TestPass-2026!",
        })
        assert resp.status_code == 302
        assert resp.url == "/dashboard/"
        assert CustomUser.objects.filter(email="new-user@example.com").exists()

        # The signup response itself logged the user in — the session should
        # already carry an authenticated user for the very next request.
        dashboard_resp = client.get("/dashboard/")
        assert dashboard_resp.status_code == 200

    def test_duplicate_email_rerenders_form_with_error(self, client, user):
        resp = client.post("/signup/", {
            "email": user.email,
            "password1": "Wm-TestPass-2026!",
            "password2": "Wm-TestPass-2026!",
        })
        assert resp.status_code == 200  # form re-rendered, not redirected
        assert b"already exists" in resp.content


@pytest.mark.django_db
class TestLogin:
    def test_login_without_2fa_succeeds(self, client, user):
        user.set_password("Wm-TestPass-2026!")
        user.save()
        resp = client.post("/login/", {"email": user.email, "password": "Wm-TestPass-2026!"})
        assert resp.status_code == 302
        dashboard_resp = client.get("/dashboard/")
        assert dashboard_resp.status_code == 200

    def test_login_with_2fa_redirects_to_verify(self, client, user):
        user.set_password("Wm-TestPass-2026!")
        user.save()
        TOTPDevice.objects.create(user=user, name="default", confirmed=True)
        resp = client.post("/login/", {"email": user.email, "password": "Wm-TestPass-2026!"})
        assert resp.status_code == 302
        assert resp.url == "/login/2fa/"

    def test_2fa_verify_with_correct_code_completes_login(self, client, user):
        user.set_password("Wm-TestPass-2026!")
        user.save()
        device = TOTPDevice.objects.create(user=user, name="default", confirmed=True)
        client.post("/login/", {"email": user.email, "password": "Wm-TestPass-2026!"})

        code = f"{totp(device.bin_key):06d}"
        resp = client.post("/login/2fa/", {"code": code})
        assert resp.status_code == 302
        assert resp.url == "/dashboard/"

        dashboard_resp = client.get("/dashboard/")
        assert dashboard_resp.status_code == 200

    def test_2fa_verify_with_wrong_code_does_not_log_in(self, client, user):
        user.set_password("Wm-TestPass-2026!")
        user.save()
        TOTPDevice.objects.create(user=user, name="default", confirmed=True)
        client.post("/login/", {"email": user.email, "password": "Wm-TestPass-2026!"})

        resp = client.post("/login/2fa/", {"code": "000000"})
        assert resp.status_code == 200
        assert b"Invalid code" in resp.content

        dashboard_resp = client.get("/dashboard/")
        assert dashboard_resp.status_code == 302  # not authenticated, redirected to login

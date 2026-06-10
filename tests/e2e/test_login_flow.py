"""End-to-end tests: full register → login → protected access → logout flow."""
import pytest


@pytest.mark.django_db
class TestLoginFlow:
    REGISTER_URL = "/api/v1/auth/register/"
    LOGIN_URL = "/api/v1/auth/login/"
    LOGOUT_URL = "/api/v1/auth/logout/"
    ME_URL = "/api/v1/auth/me/"

    def test_full_register_login_access_logout(self, api_client):
        # Step 1 — Register
        resp = api_client.post(self.REGISTER_URL, {
            "username": "e2euser",
            "email": "e2e@example.com",
            "password": "E2ePassword1!",
        })
        assert resp.status_code == 201
        token = resp.data["token"]
        assert token

        # Step 2 — Authenticated access with register token
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        resp = api_client.get(self.ME_URL)
        assert resp.status_code == 200
        assert resp.data["email"] == "e2e@example.com"

        # Step 3 — Logout
        resp = api_client.post(self.LOGOUT_URL)
        assert resp.status_code == 200

        # Step 4 — Token should now be invalid
        resp = api_client.get(self.ME_URL)
        assert resp.status_code == 401

        # Step 5 — Login again
        api_client.credentials()
        resp = api_client.post(self.LOGIN_URL, {
            "email": "e2e@example.com",
            "password": "E2ePassword1!",
        })
        assert resp.status_code == 200
        new_token = resp.data["token"]
        assert new_token

        # Step 6 — New token works
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {new_token}")
        resp = api_client.get(self.ME_URL)
        assert resp.status_code == 200

    def test_unauthenticated_cannot_access_protected(self, api_client):
        resp = api_client.get(self.ME_URL)
        assert resp.status_code == 401

    def test_wrong_password_blocked(self, api_client, user):
        resp = api_client.post(self.LOGIN_URL, {
            "email": user.email,
            "password": "wrongpassword",
        })
        assert resp.status_code == 400
        assert "token" not in resp.data

    def test_password_change_invalidates_old_token(self, api_client, user, auth_token):
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {auth_token.key}")

        resp = api_client.post("/api/v1/auth/password/change/", {
            "current_password": "testpass123",
            "new_password": "NewPassword99!",
        })
        assert resp.status_code == 200
        new_token = resp.data["token"]

        # Old token no longer works
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {auth_token.key}")
        resp = api_client.get(self.ME_URL)
        assert resp.status_code == 401

        # New token works
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {new_token}")
        resp = api_client.get(self.ME_URL)
        assert resp.status_code == 200

    def test_password_reset_request_always_200(self, api_client, user):
        resp = api_client.post("/api/v1/auth/password-reset/", {
            "email": user.email,
        })
        assert resp.status_code == 200

    def test_password_reset_unknown_email_still_200(self, api_client):
        resp = api_client.post("/api/v1/auth/password-reset/", {
            "email": "nobody@example.com",
        })
        assert resp.status_code == 200


@pytest.mark.django_db
class TestTwoFactorFlow:
    def test_2fa_setup_returns_qr(self, authed_client):
        resp = authed_client.post("/api/v1/auth/2fa/setup/")
        assert resp.status_code == 200
        assert "qr_url" in resp.data
        assert resp.data["qr_url"].startswith("data:image/png;base64,")

    def test_2fa_verify_with_invalid_code(self, authed_client):
        authed_client.post("/api/v1/auth/2fa/setup/")
        resp = authed_client.post("/api/v1/auth/2fa/verify/", {"code": "000000"})
        assert resp.status_code == 400

    def test_2fa_disable(self, authed_client):
        authed_client.post("/api/v1/auth/2fa/setup/")
        resp = authed_client.post("/api/v1/auth/2fa/disable/")
        assert resp.status_code == 200

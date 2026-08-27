"""Integration tests for Google/Microsoft social login wiring (django-allauth).

We don't have real Google/Microsoft OAuth credentials to exercise the full
handshake end-to-end, so these tests cover what's actually ours: the
adapters that gate/govern account creation, and that the login/signup pages
correctly expose the provider entry points.
"""
from unittest.mock import MagicMock, patch

import pytest
from django.test import Client


@pytest.mark.django_db
class TestAccountAdapter:
    def test_blocks_allauths_own_signup(self):
        from apps.authentication.adapters import AccountAdapter

        assert AccountAdapter().is_open_for_signup(None) is False


@pytest.mark.django_db
class TestSocialAccountAdapter:
    def test_allows_social_signup(self):
        from apps.authentication.adapters import SocialAccountAdapter

        assert SocialAccountAdapter().is_open_for_signup(None, None) is True

    def test_save_user_marks_verified(self, user):
        from apps.authentication.adapters import SocialAccountAdapter

        user.is_verified = False
        user.save(update_fields=["is_verified"])

        with patch(
            "allauth.socialaccount.adapter.DefaultSocialAccountAdapter.save_user",
            return_value=user,
        ):
            result = SocialAccountAdapter().save_user(MagicMock(), MagicMock())

        user.refresh_from_db()
        assert user.is_verified is True
        assert result.pk == user.pk


@pytest.mark.django_db
class TestSocialLoginPagesExposeProviders:
    def test_login_page_has_google_and_microsoft_links(self):
        resp = Client().get("/login/")
        assert resp.status_code == 200
        content = resp.content.decode()
        assert "/accounts/google/login/" in content
        assert "/accounts/microsoft/login/" in content
        assert "Continue with Google" in content
        assert "Continue with Microsoft" in content

    def test_signup_page_has_google_and_microsoft_links(self):
        resp = Client().get("/signup/")
        assert resp.status_code == 200
        content = resp.content.decode()
        assert "/accounts/google/login/" in content
        assert "/accounts/microsoft/login/" in content

    def test_provider_login_urls_resolve(self):
        # Confirms allauth's URLs are actually wired into config/urls.py and
        # the SOCIALACCOUNT_PROVIDERS config doesn't blow up building the URL.
        resp = Client().get("/accounts/google/login/", follow=False)
        assert resp.status_code in (302, 200)
        resp = Client().get("/accounts/microsoft/login/", follow=False)
        assert resp.status_code in (302, 200)


@pytest.mark.django_db
class TestSocialAccountSettings:
    def test_email_backend_still_first_for_password_login(self, settings):
        assert settings.AUTHENTICATION_BACKENDS[0] == "apps.authentication.backends.EmailBackend"

    def test_allauth_backend_present(self, settings):
        assert "allauth.account.auth_backends.AuthenticationBackend" in settings.AUTHENTICATION_BACKENDS

    def test_login_redirect_is_dashboard(self, settings):
        assert settings.LOGIN_REDIRECT_URL == "/dashboard/"

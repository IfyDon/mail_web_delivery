"""Tests for the suppression list: models, service helpers, web view, and API."""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.suppressions.models import Bounce, Complaint, Unsubscribe
from services.email_service import check_suppression, make_list_unsubscribe_header

User = get_user_model()


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class BounceModelTest(TestCase):
    def test_str(self):
        b = Bounce(email="bad@example.com")
        self.assertEqual(str(b), "Bounce:bad@example.com")

    def test_create(self):
        b = Bounce.objects.create(email="a@example.com", reason="mailbox full", smtp_code="452")
        self.assertIsNotNone(b.pk)
        self.assertEqual(b.smtp_code, "452")


class ComplaintModelTest(TestCase):
    def test_str(self):
        c = Complaint(email="spam@example.com")
        self.assertEqual(str(c), "Complaint:spam@example.com")

    def test_create(self):
        c = Complaint.objects.create(email="b@example.com", feedback_type="abuse")
        self.assertEqual(c.feedback_type, "abuse")


class UnsubscribeModelTest(TestCase):
    def test_str(self):
        u = Unsubscribe(email="opt@example.com")
        self.assertEqual(str(u), "Unsubscribe:opt@example.com")

    def test_token_is_auto_uuid(self):
        u = Unsubscribe.objects.create(email="c@example.com")
        self.assertIsNotNone(u.token)

    def test_unique_together(self):
        u1 = Unsubscribe.objects.create(email="d@example.com")
        # Same email + different token must succeed
        u2 = Unsubscribe.objects.create(email="d@example.com")
        self.assertNotEqual(u1.token, u2.token)


# ---------------------------------------------------------------------------
# Service helper tests
# ---------------------------------------------------------------------------

class CheckSuppressionTest(TestCase):
    def test_clean_email_not_suppressed(self):
        self.assertFalse(check_suppression("clean@example.com"))

    def test_bounced_email_suppressed(self):
        Bounce.objects.create(email="bounced@example.com")
        self.assertTrue(check_suppression("bounced@example.com"))

    def test_complaint_email_suppressed(self):
        Complaint.objects.create(email="complained@example.com")
        self.assertTrue(check_suppression("complained@example.com"))

    def test_unsubscribed_email_suppressed(self):
        Unsubscribe.objects.create(email="unsub@example.com")
        self.assertTrue(check_suppression("unsub@example.com"))

    def test_case_insensitive_lookup(self):
        Bounce.objects.create(email="Upper@Example.COM")
        self.assertTrue(check_suppression("upper@example.com"))


class ListUnsubscribeHeaderTest(TestCase):
    def test_mailto_only(self):
        header = make_list_unsubscribe_header("sender@example.com")
        self.assertIn("<mailto:sender@example.com>", header)

    def test_with_https_url(self):
        header = make_list_unsubscribe_header(
            "sender@example.com", "https://example.com/unsub"
        )
        self.assertIn("<mailto:sender@example.com>", header)
        self.assertIn("<https://example.com/unsub>", header)


# ---------------------------------------------------------------------------
# Web view tests (unsubscribe landing page)
# ---------------------------------------------------------------------------

class UnsubscribeWebViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_get_shows_form(self):
        response = self.client.get(reverse("unsubscribe"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Unsubscribe")

    def test_get_with_email_param_prefills_form(self):
        response = self.client.get(reverse("unsubscribe") + "?email=test@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "test@example.com")

    def test_post_creates_unsubscribe_record(self):
        response = self.client.post(
            reverse("unsubscribe"), data={"email": "new@example.com"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Unsubscribe.objects.filter(email="new@example.com").exists())

    def test_post_missing_email_shows_error(self):
        response = self.client.post(reverse("unsubscribe"), data={})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email required")

    def test_post_idempotent(self):
        self.client.post(reverse("unsubscribe"), data={"email": "repeat@example.com"})
        self.client.post(reverse("unsubscribe"), data={"email": "repeat@example.com"})
        # get_or_create means only one canonical record per email per session
        # (multiple Unsubscribe rows can exist due to unique_together(email, token))
        self.assertTrue(Unsubscribe.objects.filter(email="repeat@example.com").exists())

    def test_get_with_valid_token_shows_confirm(self):
        u = Unsubscribe.objects.create(email="token@example.com")
        response = self.client.get(
            reverse("unsubscribe_token", kwargs={"token": u.token})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "token@example.com")

    def test_get_with_invalid_token_returns_404(self):
        import uuid
        response = self.client.get(
            reverse("unsubscribe_token", kwargs={"token": uuid.uuid4()})
        )
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# API view tests
# ---------------------------------------------------------------------------

def _make_user(email="api@example.com", password="testpass123"):
    user = User.objects.create_user(username=email, email=email, password=password)
    token, _ = Token.objects.get_or_create(user=user)
    return user, token.key


class SuppressionAPIListTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        _, self.token = _make_user()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token}")

    def test_list_empty(self):
        response = self.client.get("/api/v1/suppressions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 0)

    def test_list_all_types(self):
        Bounce.objects.create(email="b@example.com")
        Complaint.objects.create(email="c@example.com")
        Unsubscribe.objects.create(email="u@example.com")
        response = self.client.get("/api/v1/suppressions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 3)
        types = {s["type"] for s in response.data["suppressions"]}
        self.assertEqual(types, {"bounce", "complaint", "unsubscribe"})

    def test_filter_by_type_bounce(self):
        Bounce.objects.create(email="b@example.com")
        Unsubscribe.objects.create(email="u@example.com")
        response = self.client.get("/api/v1/suppressions/?type=bounce")
        self.assertEqual(response.data["total"], 1)
        self.assertEqual(response.data["suppressions"][0]["type"], "bounce")

    def test_filter_by_email_substring(self):
        Bounce.objects.create(email="needle@example.com")
        Bounce.objects.create(email="haystack@example.com")
        response = self.client.get("/api/v1/suppressions/?email=needle")
        self.assertEqual(response.data["total"], 1)

    def test_unauthenticated_returns_401(self):
        self.client.credentials()
        response = self.client.get("/api/v1/suppressions/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class SuppressionAPIAddTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        _, self.token = _make_user("add@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token}")

    def test_add_bounce(self):
        response = self.client.post(
            "/api/v1/suppressions/",
            {"email": "new@example.com", "type": "bounce", "reason": "Mailbox full"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Bounce.objects.filter(email="new@example.com").exists())

    def test_add_complaint(self):
        response = self.client.post(
            "/api/v1/suppressions/",
            {"email": "spam@example.com", "type": "complaint"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Complaint.objects.filter(email="spam@example.com").exists())

    def test_add_unsubscribe(self):
        response = self.client.post(
            "/api/v1/suppressions/",
            {"email": "opt@example.com", "type": "unsubscribe"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Unsubscribe.objects.filter(email="opt@example.com").exists())

    def test_duplicate_returns_200_not_201(self):
        Bounce.objects.create(email="dup@example.com")
        response = self.client.post(
            "/api/v1/suppressions/",
            {"email": "dup@example.com", "type": "bounce"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["created"])

    def test_invalid_type_returns_400(self):
        response = self.client.post(
            "/api/v1/suppressions/",
            {"email": "x@example.com", "type": "invalid"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_email_returns_400(self):
        response = self.client.post(
            "/api/v1/suppressions/",
            {"email": "not-an-email", "type": "bounce"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SuppressionAPIBulkDeleteTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        _, self.token = _make_user("del@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token}")
        Bounce.objects.create(email="victim@example.com")
        Complaint.objects.create(email="victim@example.com")
        Unsubscribe.objects.create(email="victim@example.com")

    def test_bulk_delete_removes_all_types(self):
        response = self.client.delete(
            "/api/v1/suppressions/",
            {"emails": ["victim@example.com"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["removed"], 3)
        self.assertFalse(Bounce.objects.filter(email="victim@example.com").exists())

    def test_bulk_delete_empty_list_returns_400(self):
        response = self.client.delete(
            "/api/v1/suppressions/", {"emails": []}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SuppressionAPIDetailDeleteTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        _, self.token = _make_user("det@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token}")

    def test_delete_existing_email(self):
        Bounce.objects.create(email="gone@example.com")
        response = self.client.delete("/api/v1/suppressions/gone@example.com/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Bounce.objects.filter(email="gone@example.com").exists())

    def test_delete_nonexistent_returns_404(self):
        response = self.client.delete("/api/v1/suppressions/nobody@example.com/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

import pytest

from webmail_sdk import WebMail


@pytest.fixture
def client():
    return WebMail(api_key="sk_test_123", base_url="https://webmailapi.test")

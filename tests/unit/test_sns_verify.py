"""Unit tests for AWS SNS message signature verification
(integrations/ses/sns_verify.py) — the fix for the unauthenticated
SES/SNS webhook finding."""
import base64
import datetime
import uuid
from unittest.mock import patch

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID

from integrations.ses.sns_verify import is_trusted_aws_url, verify_sns_message


@pytest.fixture(scope="module")
def keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "sns.amazonaws.com")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1))
        .sign(private_key, hashes.SHA256())
    )
    pem = cert.public_bytes(serialization.Encoding.PEM)
    return private_key, pem


def _sign(private_key, canonical: str) -> str:
    signature = private_key.sign(canonical.encode("utf-8"), padding.PKCS1v15(), hashes.SHA1())
    return base64.b64encode(signature).decode("ascii")


def _notification_body(private_key, cert_url, **overrides):
    body = {
        "Type": "Notification",
        "MessageId": "msg-1",
        "TopicArn": "arn:aws:sns:us-east-1:123456789012:webmail-email-events",
        "Message": '{"notificationType":"Bounce"}',
        "Timestamp": "2024-01-01T00:00:00.000Z",
        "SigningCertURL": cert_url,
        "SignatureVersion": "1",
    }
    body.update(overrides)
    canonical = "\n".join(
        f"{f}\n{body[f]}" for f in ("Message", "MessageId", "Subject", "Timestamp", "TopicArn", "Type")
        if f in body
    ) + "\n"
    body["Signature"] = _sign(private_key, canonical)
    return body


class TestIsTrustedAwsUrl:
    def test_accepts_real_regional_sns_host(self):
        assert is_trusted_aws_url("https://sns.us-east-1.amazonaws.com/cert.pem")

    def test_rejects_lookalike_host(self):
        assert not is_trusted_aws_url("https://sns.us-east-1.amazonaws.com.attacker.com/cert.pem")

    def test_rejects_non_sns_subdomain(self):
        assert not is_trusted_aws_url("https://attacker.com/sns.us-east-1.amazonaws.com")

    def test_rejects_http_scheme(self):
        assert not is_trusted_aws_url("http://sns.us-east-1.amazonaws.com/cert.pem")


@pytest.fixture
def cert_url():
    # Unique per test so the shared Redis-backed cache (1h TTL) never serves
    # a stale cert from a prior test run under the same key.
    return f"https://sns.us-east-1.amazonaws.com/test-cert-{uuid.uuid4().hex}.pem"


@pytest.mark.django_db
class TestVerifySnsMessage:
    def test_valid_signature_accepted(self, keypair, cert_url):
        private_key, pem = keypair
        body = _notification_body(private_key, cert_url)
        with patch("integrations.ses.sns_verify.urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = pem
            assert verify_sns_message(body) is True

    def test_tampered_message_rejected(self, keypair, cert_url):
        private_key, pem = keypair
        body = _notification_body(private_key, cert_url)
        body["Message"] = '{"notificationType":"Complaint"}'  # signed over the original value
        with patch("integrations.ses.sns_verify.urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = pem
            assert verify_sns_message(body) is False

    def test_signature_from_different_key_rejected(self, keypair, cert_url):
        _private_key, pem = keypair
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        body = _notification_body(other_key, cert_url)  # signed with a different key than the served cert
        with patch("integrations.ses.sns_verify.urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = pem
            assert verify_sns_message(body) is False

    def test_untrusted_cert_host_rejected_without_fetching(self, keypair):
        private_key, _pem = keypair
        body = _notification_body(private_key, "https://sns.attacker.com/cert.pem")
        with patch("integrations.ses.sns_verify.urllib.request.urlopen") as mock_open:
            assert verify_sns_message(body) is False
            mock_open.assert_not_called()

    def test_missing_signature_rejected(self, cert_url):
        body = {"Type": "Notification", "SigningCertURL": cert_url}
        assert verify_sns_message(body) is False

    def test_unsupported_type_rejected(self, keypair, cert_url):
        private_key, pem = keypair
        body = _notification_body(private_key, cert_url, Type="UnsubscribeConfirmation")
        # Signed for Notification fields but claiming a different Type — canonical
        # string won't match what was actually signed, so this must fail closed.
        with patch("integrations.ses.sns_verify.urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = pem
            assert verify_sns_message(body) is False

    def test_topic_arn_allowlist_rejects_unexpected_topic(self, keypair, cert_url, settings):
        private_key, pem = keypair
        settings.AWS_SNS_EXPECTED_TOPIC_ARNS = ["arn:aws:sns:us-east-1:123456789012:some-other-topic"]
        body = _notification_body(private_key, cert_url)
        with patch("integrations.ses.sns_verify.urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = pem
            assert verify_sns_message(body) is False

    def test_topic_arn_allowlist_accepts_listed_topic(self, keypair, cert_url, settings):
        private_key, pem = keypair
        settings.AWS_SNS_EXPECTED_TOPIC_ARNS = ["arn:aws:sns:us-east-1:123456789012:webmail-email-events"]
        body = _notification_body(private_key, cert_url)
        with patch("integrations.ses.sns_verify.urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = pem
            assert verify_sns_message(body) is True

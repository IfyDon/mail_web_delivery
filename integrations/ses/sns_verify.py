"""AWS SNS message signature verification.

Every inbound SNS notification (SES bounce/complaint, SES inbound-mail
receipt) arrives as an unauthenticated HTTPS POST — AWS has no way to send
an API key. Authenticity instead relies entirely on verifying the message
signature per AWS's documented algorithm: build the canonical string from
the signed fields, fetch the signing certificate from SigningCertURL, and
verify the RSA signature against it.

https://docs.aws.amazon.com/sns/latest/dg/sns-verify-signature-of-message.html
"""
import base64
import logging
import re
import urllib.request
from urllib.parse import urlparse

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Real SNS signing certs and SubscribeURLs are always served from a
# regional SNS domain over HTTPS — anything else is not AWS.
_TRUSTED_HOST_RE = re.compile(r"^sns\.[a-z0-9-]+\.amazonaws\.com(\.cn)?$")

_NOTIFICATION_FIELDS = ("Message", "MessageId", "Subject", "Timestamp", "TopicArn", "Type")
_SUBSCRIPTION_FIELDS = ("Message", "MessageId", "SubscribeURL", "Timestamp", "Token", "TopicArn", "Type")


def is_trusted_aws_url(url: str) -> bool:
    """True if *url* is an https:// URL on a real SNS regional domain."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return parsed.scheme == "https" and bool(_TRUSTED_HOST_RE.match(parsed.hostname or ""))


def _canonical_string(body: dict) -> str | None:
    msg_type = body.get("Type", "")
    if msg_type == "Notification":
        fields = _NOTIFICATION_FIELDS
    elif msg_type in ("SubscriptionConfirmation", "UnsubscribeConfirmation"):
        fields = _SUBSCRIPTION_FIELDS
    else:
        return None

    parts = []
    for field in fields:
        if field == "Subject" and "Subject" not in body:
            continue  # Subject is only part of the signed string when present
        if field not in body:
            return None
        parts.append(field)
        parts.append(str(body[field]))
    return "\n".join(parts) + "\n"


def _fetch_cert_pem(cert_url: str) -> bytes | None:
    cache_key = f"sns_signing_cert:{cert_url}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        with urllib.request.urlopen(cert_url, timeout=5) as resp:  # noqa: S310 — host pre-validated by is_trusted_aws_url
            pem = resp.read()
    except Exception as exc:  # noqa: BLE001 — any fetch failure just fails verification
        logger.error("sns_verify: failed to fetch signing cert %s: %s", cert_url, exc)
        return None
    cache.set(cache_key, pem, timeout=3600)
    return pem


def verify_sns_message(body: dict) -> bool:
    """Verify an inbound SNS message is authentically signed by AWS.

    Returns False (never raises) for anything malformed, unsigned, or
    failing verification — callers should reject the request outright.
    """
    cert_url = body.get("SigningCertURL", "")
    if not is_trusted_aws_url(cert_url):
        logger.warning("sns_verify: rejected — untrusted SigningCertURL %r", cert_url)
        return False

    signature_b64 = body.get("Signature", "")
    if not signature_b64:
        logger.warning("sns_verify: rejected — missing Signature")
        return False

    canonical = _canonical_string(body)
    if canonical is None:
        logger.warning("sns_verify: rejected — unsupported Type or missing signed field")
        return False

    expected_arns = getattr(settings, "AWS_SNS_EXPECTED_TOPIC_ARNS", None)
    if expected_arns and body.get("TopicArn") not in expected_arns:
        logger.warning("sns_verify: rejected — unexpected TopicArn %r", body.get("TopicArn"))
        return False

    pem = _fetch_cert_pem(cert_url)
    if pem is None:
        return False

    try:
        signature = base64.b64decode(signature_b64)
        public_key = x509.load_pem_x509_certificate(pem).public_key()
        hash_algo = hashes.SHA256() if body.get("SignatureVersion") == "2" else hashes.SHA1()
        public_key.verify(signature, canonical.encode("utf-8"), padding.PKCS1v15(), hash_algo)
    except (InvalidSignature, ValueError, TypeError) as exc:
        logger.warning("sns_verify: rejected — signature check failed: %s", exc)
        return False

    return True

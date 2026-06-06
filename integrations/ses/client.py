"""Simple SES client wrapper used by workers/tasks/send_email.py.

Uses boto3 if available. The `send_email` method accepts headers and payload
as returned by `services.email_service.send_email()` and attempts to send
via Amazon SES using `send_raw_email` when possible.
"""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


class SESClient:
    def __init__(self):
        try:
            import boto3

            self.client = boto3.client("ses")
        except Exception:
            self.client = None

    def send_email(self, headers: dict, payload: dict) -> dict:
        """Send an email via SES. Returns provider response dict or raises.

        If boto3 is not available, raises RuntimeError.
        """
        if not self.client:
            raise RuntimeError("boto3 not available or SES not configured")

        # Build a simple multipart/alternative message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = headers.get("Subject")
        msg["From"] = headers.get("From")
        msg["To"] = headers.get("To")
        if "List-Unsubscribe" in headers:
            msg["List-Unsubscribe"] = headers["List-Unsubscribe"]

        text = payload.get("text", "")
        html = payload.get("html", "")

        if text:
            part1 = MIMEText(text, "plain", _charset="utf-8")
            msg.attach(part1)
        if html:
            part2 = MIMEText(html, "html", _charset="utf-8")
            msg.attach(part2)

        raw = msg.as_string()
        resp = self.client.send_raw_email(RawMessage={"Data": raw})
        logger.info("SES send_raw_email response: %s", resp)
        return resp


"""Simple SES client wrapper used by workers/tasks/send_email.py.

Uses boto3 if available. The `send_email` method accepts headers and payload
as returned by `services.email_service.send_email()` and attempts to send
via Amazon SES using `send_raw_email` when possible.
"""

import logging
from email.mime.application import MIMEApplication
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

        to_address = headers.get("To")
        cc_addresses = headers.get("Cc") or []
        bcc_addresses = headers.get("Bcc") or []

        outer = MIMEMultipart("mixed")
        outer["Subject"] = headers.get("Subject")
        outer["From"] = headers.get("From")
        outer["To"] = to_address
        if cc_addresses:
            outer["Cc"] = ", ".join(cc_addresses)
        if headers.get("Reply-To"):
            outer["Reply-To"] = headers["Reply-To"]
        if "List-Unsubscribe" in headers:
            outer["List-Unsubscribe"] = headers["List-Unsubscribe"]
        if "List-Unsubscribe-Post" in headers:
            outer["List-Unsubscribe-Post"] = headers["List-Unsubscribe-Post"]
        # Bcc is deliberately never set as a header — it must stay invisible to
        # every recipient. It's routed purely via the Destinations list below.

        body = MIMEMultipart("alternative")
        text = payload.get("text", "")
        html = payload.get("html", "")
        if text:
            body.attach(MIMEText(text, "plain", _charset="utf-8"))
        if html:
            body.attach(MIMEText(html, "html", _charset="utf-8"))
        outer.attach(body)

        for att in payload.get("attachments", []):
            part = MIMEApplication(att["content"])
            part.add_header(
                "Content-Disposition", "attachment", filename=att["filename"]
            )
            if att.get("content_type"):
                part.set_type(att["content_type"])
            outer.attach(part)

        destinations = [to_address, *cc_addresses, *bcc_addresses]

        resp = self.client.send_raw_email(
            Destinations=destinations,
            RawMessage={"Data": outer.as_string()},
        )
        logger.info("SES send_raw_email response: %s", resp)
        return resp

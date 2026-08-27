"""SMTP relay client — fallback when SES is not configured."""

import logging
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


class SMTPClient:
    """Send email via a generic SMTP relay.

    Required env vars: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD
    Optional:          SMTP_USE_TLS (default 'true')
    """

    def __init__(self):
        self.host = os.getenv('SMTP_HOST', 'localhost')
        self.port = int(os.getenv('SMTP_PORT', '587'))
        self.user = os.getenv('SMTP_USER', '')
        self.password = os.getenv('SMTP_PASSWORD', '')
        self.use_tls = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'

    def send_email(self, headers: dict, payload: dict) -> dict:
        """Send via SMTP. Returns a minimal response dict or raises on failure."""
        to_address = headers.get('To', '')
        cc_addresses = headers.get('Cc') or []
        bcc_addresses = headers.get('Bcc') or []

        msg = MIMEMultipart('mixed')
        msg['Subject'] = headers.get('Subject', '')
        msg['From'] = headers.get('From', '')
        msg['To'] = to_address
        if cc_addresses:
            msg['Cc'] = ', '.join(cc_addresses)
        if headers.get('Reply-To'):
            msg['Reply-To'] = headers['Reply-To']
        for key in ('List-Unsubscribe', 'List-Unsubscribe-Post'):
            if key in headers:
                msg[key] = headers[key]
        # Bcc is never set as a header — routed only via the envelope recipient
        # list passed to sendmail() below, so it stays invisible to recipients.

        body = MIMEMultipart('alternative')
        text = payload.get('text', '')
        html = payload.get('html', '')
        if text:
            body.attach(MIMEText(text, 'plain', _charset='utf-8'))
        if html:
            body.attach(MIMEText(html, 'html', _charset='utf-8'))
        msg.attach(body)

        for att in payload.get('attachments', []):
            part = MIMEApplication(att['content'])
            part.add_header('Content-Disposition', 'attachment', filename=att['filename'])
            if att.get('content_type'):
                part.set_type(att['content_type'])
            msg.attach(part)

        envelope_to = [to_address, *cc_addresses, *bcc_addresses]

        with smtplib.SMTP(self.host, self.port, timeout=30) as conn:
            if self.use_tls:
                conn.starttls()
            if self.user and self.password:
                conn.login(self.user, self.password)
            conn.sendmail(msg['From'], envelope_to, msg.as_string())

        logger.info('SMTP sent %s → %s', msg['From'], envelope_to)
        return {'MessageId': '', 'provider': 'smtp'}

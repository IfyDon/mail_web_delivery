"""SMTP relay client — fallback when SES is not configured."""

import logging
import os
import smtplib
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
        msg = MIMEMultipart('alternative')
        msg['Subject'] = headers.get('Subject', '')
        msg['From'] = headers.get('From', '')
        msg['To'] = headers.get('To', '')
        for key in ('List-Unsubscribe', 'List-Unsubscribe-Post'):
            if key in headers:
                msg[key] = headers[key]

        text = payload.get('text', '')
        html = payload.get('html', '')
        if text:
            msg.attach(MIMEText(text, 'plain', _charset='utf-8'))
        if html:
            msg.attach(MIMEText(html, 'html', _charset='utf-8'))

        with smtplib.SMTP(self.host, self.port, timeout=30) as conn:
            if self.use_tls:
                conn.starttls()
            if self.user and self.password:
                conn.login(self.user, self.password)
            conn.sendmail(msg['From'], [msg['To']], msg.as_string())

        logger.info('SMTP sent %s → %s', msg['From'], msg['To'])
        return {'MessageId': '', 'provider': 'smtp'}

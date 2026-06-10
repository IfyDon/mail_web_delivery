"""Celery task: load Message from DB, render template, send via relay, update status."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)

# Exponential backoff countdowns (seconds): 30s, 2m, 10m, 1h, 6h
_RETRY_DELAYS = [30, 120, 600, 3600, 21600]


@shared_task(bind=True, max_retries=5, acks_late=True)
def send_email_task(self, message_id: str) -> dict:
    """Send a queued Message record via the configured relay (SES → SMTP fallback)."""
    from django.conf import settings
    from apps.email_messages.models import Message
    from apps.events.models import Event
    from services.email_service import check_suppression, make_list_unsubscribe_header
    from tracking.tokens import generate_unsubscribe_token

    try:
        msg = Message.objects.select_related('domain', 'template_version', 'user').get(
            pk=message_id
        )
    except Message.DoesNotExist:
        logger.error('send_email_task: Message %s not found', message_id)
        return {'status': 'error', 'reason': 'message_not_found'}

    # Idempotency guard
    if msg.status not in (Message.STATUS_QUEUED, Message.STATUS_FAILED):
        logger.info('send_email_task: %s already %s, skipping', message_id, msg.status)
        return {'status': msg.status}

    # Account-level sending pause (set by bounce-rate alerting when threshold exceeded)
    if msg.user.sending_paused:
        msg.status = Message.STATUS_FAILED
        msg.save(update_fields=['status', 'updated_at'])
        logger.warning(
            'send_email_task: account %s sending paused — skipping %s',
            msg.user_id, message_id,
        )
        return {'status': 'failed', 'reason': 'sending_paused'}

    # Per-user suppression check
    if check_suppression(msg.to_address, user=msg.user):
        msg.status = Message.STATUS_SUPPRESSED
        msg.save(update_fields=['status', 'updated_at'])
        logger.info('send_email_task: %s suppressed', msg.to_address)
        return {'status': 'suppressed'}

    # Render template if not already embedded
    html = msg.html_body
    text = msg.text_body
    if msg.template_version and not html:
        try:
            from services.template_service import render_template
            rendered = render_template(msg.template_version, context={})
            html = rendered.get('html', '')
            text = rendered.get('text', '')
        except Exception as exc:
            logger.exception('send_email_task: template render failed for %s', message_id)
            return _handle_retry(self, msg, exc)

    # Inject open pixel + rewrite click links (UTM campaign = stream name)
    if html and (msg.track_opens or msg.track_clicks):
        from services.tracking_service import inject_tracking
        html = inject_tracking(html, str(msg.pk), utm_campaign=msg.stream or "")

    # Build real one-click unsubscribe URL
    base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
    unsub_token = generate_unsubscribe_token(str(msg.user_id), msg.to_address)
    unsubscribe_url = f"{base_url}/unsubscribe/{unsub_token}/"

    headers = {
        'From': msg.from_address,
        'To': msg.to_address,
        'Subject': msg.subject,
        'List-Unsubscribe': make_list_unsubscribe_header(msg.from_address, unsubscribe_url),
        'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click',
    }

    # CAN-SPAM §5(a)(6): every commercial email must include a valid physical address.
    physical_address = getattr(settings, 'PHYSICAL_ADDRESS', '')
    if physical_address:
        footer_html = (
            f'<div style="font-size:11px;color:#888;margin-top:24px;text-align:center">'
            f'{physical_address} &nbsp;·&nbsp; '
            f'<a href="{unsubscribe_url}" style="color:#888">Unsubscribe</a>'
            f'</div>'
        )
        footer_text = f'\n\n--\n{physical_address}\nUnsubscribe: {unsubscribe_url}\n'
        if html:
            html = html + footer_html
        if text:
            text = text + footer_text

    payload = {'html': html, 'text': text}

    msg.status = Message.STATUS_SENDING
    msg.attempts += 1
    msg.save(update_fields=['status', 'attempts', 'updated_at'])

    try:
        provider_resp = _relay(headers, payload)
    except Exception as exc:
        logger.warning(
            'send_email_task: relay failed for %s (attempt %d): %s',
            message_id, msg.attempts, exc,
        )
        return _handle_retry(self, msg, exc)

    provider_id = provider_resp.get('MessageId', '')
    msg.status = Message.STATUS_SENT
    msg.provider_message_id = provider_id
    msg.save(update_fields=['status', 'provider_message_id', 'updated_at'])

    Event.objects.create(
        message=msg,
        type=Event.TYPE_DELIVERED,
        metadata={'provider_message_id': provider_id, 'attempt': msg.attempts},
    )

    from services.webhook_service import build_event_payload, trigger_webhooks
    trigger_webhooks(
        msg.user,
        'delivered',
        build_event_payload('delivered', str(msg.pk), {'provider_message_id': provider_id}),
    )

    logger.info('send_email_task: sent %s (provider_id=%s)', message_id, provider_id)
    return {'status': 'sent', 'provider_message_id': provider_id}


def _relay(headers: dict, payload: dict) -> dict:
    """Try SES → SMTP → Django email backend (dev console fallback)."""
    from integrations.ses.client import SESClient
    from integrations.smtp.client import SMTPClient

    try:
        return SESClient().send_email(headers, payload)
    except RuntimeError:
        pass  # SES not configured

    try:
        return SMTPClient().send_email(headers, payload)
    except Exception:
        pass  # SMTP not configured (e.g. local dev)

    # Final fallback: Django's configured EMAIL_BACKEND (console in dev)
    from django.core.mail import EmailMultiAlternatives
    mail = EmailMultiAlternatives(
        subject=headers.get('Subject', ''),
        body=payload.get('text', '') or payload.get('html', ''),
        from_email=headers.get('From', ''),
        to=[headers.get('To', '')],
        headers={k: v for k, v in headers.items() if k not in ('Subject', 'From', 'To')},
    )
    if payload.get('html'):
        mail.attach_alternative(payload['html'], 'text/html')
    mail.send()
    return {'MessageId': 'dev-console', 'provider': 'django'}


def _handle_retry(self, msg, exc: Exception) -> dict:
    """Schedule a retry or mark permanently failed when retries exhausted."""
    from apps.email_messages.models import Message
    from services.webhook_service import build_event_payload, trigger_webhooks

    idx = self.request.retries
    countdown = _RETRY_DELAYS[idx] if idx < len(_RETRY_DELAYS) else _RETRY_DELAYS[-1]

    msg.status = Message.STATUS_FAILED
    msg.save(update_fields=['status', 'updated_at'])

    if idx < self.max_retries:
        raise self.retry(exc=exc, countdown=countdown)

    msg.status = Message.STATUS_PERMANENTLY_FAILED
    msg.save(update_fields=['status', 'updated_at'])
    logger.error(
        'send_email_task: permanently failed %s after %d attempts', msg.pk, msg.attempts
    )
    trigger_webhooks(
        msg.user,
        'permanently_failed',
        build_event_payload('permanently_failed', str(msg.pk)),
    )
    return {'status': 'permanently_failed'}

"""
Celery task: parse inbound ESP delivery-status webhook payloads, create Event
records, update Message status, and fire user-facing webhooks.

Supported sources: 'ses' (AWS SNS delivery notifications), 'sendgrid'.

Usage:
    process_inbound_event.delay(payload_dict, source='ses')
    process_inbound_event.delay(payload_dict, source='sendgrid')
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)

# Maps raw ESP event names → internal Event.TYPE_* values
_SES_EVENT_MAP = {
    'Delivery': 'delivered',
    'Bounce': 'bounce',
    'Complaint': 'complaint',
    'Open': 'open',
    'Click': 'click',
}

_SENDGRID_EVENT_MAP = {
    'delivered': 'delivered',
    'bounce': 'bounce',
    'blocked': 'bounce',
    'spamreport': 'complaint',
    'open': 'open',
    'click': 'click',
    'unsubscribe': 'unsubscribe',
    'group_unsubscribe': 'unsubscribe',
}

# Message statuses we set based on the received event type
_EVENT_TO_STATUS = {
    'delivered': 'delivered',
    'bounce': 'permanently_failed',
}


@shared_task
def process_inbound_event(payload: dict, source: str) -> dict:
    """Parse an ESP event payload, persist an Event, update Message status."""
    from apps.email_messages.models import Message
    from apps.events.models import Event

    try:
        provider_message_id, event_type, metadata = _parse_payload(payload, source)
    except (KeyError, ValueError) as exc:
        logger.warning('process_inbound_event: parse error source=%s: %s', source, exc)
        return {'status': 'parse_error', 'error': str(exc)}

    if not provider_message_id or not event_type:
        logger.debug('process_inbound_event: ignored source=%s type=%s', source, event_type)
        return {'status': 'ignored'}

    try:
        msg = Message.objects.get(provider_message_id=provider_message_id)
    except Message.DoesNotExist:
        logger.debug(
            'process_inbound_event: no message for provider_id=%s', provider_message_id
        )
        return {'status': 'not_found', 'provider_message_id': provider_message_id}
    except Message.MultipleObjectsReturned:
        msg = (
            Message.objects
            .filter(provider_message_id=provider_message_id)
            .latest('created_at')
        )

    Event.objects.create(message=msg, type=event_type, metadata=metadata)
    _update_message_status(msg, event_type)
    _fire_webhook(msg, event_type, metadata)

    logger.info(
        'process_inbound_event: processed source=%s event=%s message=%s',
        source, event_type, msg.pk,
    )
    return {'status': 'processed', 'message_id': str(msg.pk), 'event': event_type}


# ── Parsers ───────────────────────────────────────────────────────────────────

def _parse_payload(payload: dict, source: str) -> tuple:
    if source == 'ses':
        return _parse_ses(payload)
    if source == 'sendgrid':
        return _parse_sendgrid(payload)
    raise ValueError(f'Unknown source: {source!r}')


def _parse_ses(payload: dict) -> tuple:
    """Parse an AWS SES delivery/bounce/complaint notification (unwrapped from SNS)."""
    notification_type = payload.get('notificationType', '')
    mail = payload.get('mail', {})
    provider_id = mail.get('messageId', '')
    event_type = _SES_EVENT_MAP.get(notification_type, '')
    metadata: dict = {'source': 'ses', 'raw_type': notification_type}

    if notification_type == 'Delivery':
        delivery = payload.get('delivery', {})
        metadata['smtp_response'] = delivery.get('smtpResponse', '')
        metadata['recipients'] = delivery.get('recipients', [])

    elif notification_type == 'Bounce':
        bounce = payload.get('bounce', {})
        metadata['bounce_type'] = bounce.get('bounceType', '')
        metadata['bounce_subtype'] = bounce.get('bounceSubType', '')
        metadata['recipients'] = [
            r.get('emailAddress') for r in bounce.get('bouncedRecipients', [])
        ]
        metadata['diagnostic_code'] = (
            bounce.get('bouncedRecipients', [{}])[0].get('diagnosticCode', '')
            if bounce.get('bouncedRecipients') else ''
        )

    elif notification_type == 'Complaint':
        complaint = payload.get('complaint', {})
        metadata['feedback_type'] = complaint.get('complaintFeedbackType', '')
        metadata['recipients'] = [
            r.get('emailAddress') for r in complaint.get('complainedRecipients', [])
        ]

    elif notification_type == 'Open':
        metadata['ip_address'] = payload.get('open', {}).get('ipAddress', '')
        metadata['user_agent'] = payload.get('open', {}).get('userAgent', '')

    elif notification_type == 'Click':
        metadata['link'] = payload.get('click', {}).get('link', '')
        metadata['ip_address'] = payload.get('click', {}).get('ipAddress', '')

    return provider_id, event_type, metadata


def _parse_sendgrid(payload: dict) -> tuple:
    """Parse a single SendGrid event object (SendGrid posts arrays; caller should split)."""
    sg_type = payload.get('event', '')
    # sg_message_id has the format "<uuid>.<filter_id>" — we only store the first part
    provider_id = payload.get('sg_message_id', '').split('.')[0]
    event_type = _SENDGRID_EVENT_MAP.get(sg_type, '')
    metadata: dict = {
        'source': 'sendgrid',
        'raw_type': sg_type,
        'email': payload.get('email', ''),
        'timestamp': payload.get('timestamp', ''),
    }
    if sg_type == 'click':
        metadata['url'] = payload.get('url', '')
    elif sg_type in ('bounce', 'blocked'):
        metadata['reason'] = payload.get('reason', '')
        metadata['smtp_code'] = str(payload.get('status', ''))
        metadata['bounce_type'] = 'hard' if sg_type == 'bounce' else 'soft'
    elif sg_type == 'open':
        metadata['ip'] = payload.get('ip', '')
        metadata['user_agent'] = payload.get('useragent', '')

    return provider_id, event_type, metadata


# ── Helpers ───────────────────────────────────────────────────────────────────

def _update_message_status(msg, event_type: str) -> None:
    from apps.email_messages.models import Message

    new_status = _EVENT_TO_STATUS.get(event_type)
    if new_status and msg.status != new_status:
        Message.objects.filter(pk=msg.pk).update(status=new_status)


def _fire_webhook(msg, event_type: str, metadata: dict) -> None:
    try:
        from services.webhook_service import build_event_payload, trigger_webhooks
        payload = build_event_payload(event_type, str(msg.pk), metadata)
        trigger_webhooks(msg.user, event_type, payload)
    except Exception:
        logger.exception('process_inbound_event: webhook failed for message %s', msg.pk)

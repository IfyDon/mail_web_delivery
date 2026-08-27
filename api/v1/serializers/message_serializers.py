"""Serializers for email sending and message history endpoints."""
import base64
import binascii

from rest_framework import serializers
from django.core.validators import validate_email as _django_validate_email
from django.core.exceptions import ValidationError as _DjangoValidationError

from apps.email_messages.models import Message
from apps.events.models import Event

# SES/most relays cap the raw message (body + attachments) around 10 MB.
# Leave headroom for headers/MIME boundaries.
MAX_ATTACHMENT_TOTAL_BYTES = 9 * 1024 * 1024
MAX_ATTACHMENTS_PER_MESSAGE = 10


class FlexibleToField(serializers.Field):
    """Accept 'to' as a plain email string, ["email"], or [{"email": "..."}]."""

    def to_internal_value(self, data):
        # Unwrap list -> first element
        if isinstance(data, list):
            if not data:
                self.fail('required')
            data = data[0]
        # Unwrap {"email": "..."} dict
        if isinstance(data, dict):
            data = data.get('email') or data.get('address') or ''
        if not isinstance(data, str) or not data:
            raise serializers.ValidationError('Enter a valid email address.')
        try:
            _django_validate_email(data)
        except _DjangoValidationError:
            raise serializers.ValidationError('Enter a valid email address.')
        return data

    def to_representation(self, value):
        return value


class AttachmentSerializer(serializers.Serializer):
    filename = serializers.CharField(max_length=255)
    content_type = serializers.CharField(
        max_length=100, required=False, default="application/octet-stream"
    )
    content = serializers.CharField(help_text="Base64-encoded file content.")

    def validate_content(self, value):
        try:
            decoded = base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError):
            raise serializers.ValidationError("content must be valid base64.")
        if not decoded:
            raise serializers.ValidationError("Attachment content cannot be empty.")
        return value


class SendEmailSerializer(serializers.Serializer):
    to = FlexibleToField()
    from_address = serializers.EmailField()
    reply_to = serializers.EmailField(required=False, allow_blank=True, default="")
    cc = serializers.ListField(
        child=serializers.EmailField(), required=False, default=list, max_length=50
    )
    bcc = serializers.ListField(
        child=serializers.EmailField(), required=False, default=list, max_length=50
    )
    subject = serializers.CharField(max_length=998)
    html_body = serializers.CharField(required=False, allow_blank=True, default="")
    text_body = serializers.CharField(required=False, allow_blank=True, default="")
    template_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    template_data = serializers.DictField(
        child=serializers.CharField(), required=False, default=dict
    )
    stream = serializers.ChoiceField(
        choices=Message.STREAM_CHOICES, default=Message.STREAM_TRANSACTIONAL
    )
    track_opens = serializers.BooleanField(default=True)
    track_clicks = serializers.BooleanField(default=True)
    send_at = serializers.DateTimeField(required=False, allow_null=True, default=None)
    attachments = AttachmentSerializer(many=True, required=False, default=list)

    # Rename incoming "from" → "from_address" so it doesn't collide with the keyword
    def to_internal_value(self, data):
        if "from" in data and "from_address" not in data:
            data = dict(data)
            data["from_address"] = data.pop("from")
        return super().to_internal_value(data)

    def validate_attachments(self, value):
        if len(value) > MAX_ATTACHMENTS_PER_MESSAGE:
            raise serializers.ValidationError(
                f"A message can have at most {MAX_ATTACHMENTS_PER_MESSAGE} attachments."
            )
        total = sum(len(base64.b64decode(a["content"])) for a in value)
        if total > MAX_ATTACHMENT_TOTAL_BYTES:
            raise serializers.ValidationError(
                f"Total attachment size ({total} bytes) exceeds the "
                f"{MAX_ATTACHMENT_TOTAL_BYTES} byte limit."
            )
        return value

    def validate(self, attrs):
        has_body = attrs.get("html_body") or attrs.get("text_body")
        has_template = attrs.get("template_id")
        if not has_body and not has_template:
            raise serializers.ValidationError(
                "Provide either html_body/text_body or a template_id."
            )
        return attrs


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ["type", "timestamp", "metadata"]


class MessageListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = [
            "id", "to_address", "from_address", "subject",
            "status", "stream", "created_at",
        ]


class MessageAttachmentSerializer(serializers.Serializer):
    filename = serializers.CharField()
    content_type = serializers.CharField()
    size = serializers.IntegerField()


class MessageDetailSerializer(serializers.ModelSerializer):
    events = EventSerializer(many=True, read_only=True)
    attachments = MessageAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = [
            "id", "to_address", "from_address", "reply_to",
            "cc_addresses", "bcc_addresses", "subject",
            "html_body", "text_body", "status", "stream",
            "attempts", "provider_message_id", "track_opens", "track_clicks",
            "created_at", "updated_at", "events", "attachments",
        ]

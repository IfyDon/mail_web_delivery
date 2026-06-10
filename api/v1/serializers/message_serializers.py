"""Serializers for email sending and message history endpoints."""
from rest_framework import serializers
from django.core.validators import validate_email as _django_validate_email
from django.core.exceptions import ValidationError as _DjangoValidationError

from apps.email_messages.models import Message
from apps.events.models import Event


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


class SendEmailSerializer(serializers.Serializer):
    to = FlexibleToField()
    from_address = serializers.EmailField()
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

    # Rename incoming "from" → "from_address" so it doesn't collide with the keyword
    def to_internal_value(self, data):
        if "from" in data and "from_address" not in data:
            data = dict(data)
            data["from_address"] = data.pop("from")
        return super().to_internal_value(data)

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


class MessageDetailSerializer(serializers.ModelSerializer):
    events = EventSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = [
            "id", "to_address", "from_address", "subject",
            "html_body", "text_body", "status", "stream",
            "attempts", "provider_message_id", "track_opens", "track_clicks",
            "created_at", "updated_at", "events",
        ]

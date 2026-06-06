"""Serializers for email sending and message history endpoints."""
from rest_framework import serializers

from apps.email_messages.models import Message
from apps.events.models import Event


class SendEmailSerializer(serializers.Serializer):
    to = serializers.EmailField()
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

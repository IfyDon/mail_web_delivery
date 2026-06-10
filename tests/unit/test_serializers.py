"""Unit tests for DRF serializers."""
import pytest


@pytest.mark.django_db
class TestFlexibleToField:
    def _serialize(self, value):
        from api.v1.serializers.message_serializers import FlexibleToField
        field = FlexibleToField()
        return field.to_internal_value(value)

    def test_plain_string(self):
        assert self._serialize("user@example.com") == "user@example.com"

    def test_list_with_one_email(self):
        assert self._serialize(["user@example.com"]) == "user@example.com"

    def test_dict_with_email_key(self):
        assert self._serialize({"email": "user@example.com"}) == "user@example.com"

    def test_dict_with_address_key(self):
        assert self._serialize({"address": "user@example.com"}) == "user@example.com"

    def test_invalid_email_raises(self):
        from rest_framework.exceptions import ValidationError
        from api.v1.serializers.message_serializers import FlexibleToField
        field = FlexibleToField()
        with pytest.raises(ValidationError):
            field.to_internal_value("not-an-email")

    def test_empty_list_raises(self):
        from rest_framework.exceptions import ValidationError
        from api.v1.serializers.message_serializers import FlexibleToField
        field = FlexibleToField()
        with pytest.raises((ValidationError, Exception)):
            field.to_internal_value([])


@pytest.mark.django_db
class TestSendEmailSerializer:
    def _valid_data(self, **overrides):
        data = {
            "to": "recipient@example.com",
            "from_address": "sender@example.com",
            "subject": "Hello",
            "html_body": "<p>Hi</p>",
        }
        data.update(overrides)
        return data

    def test_valid_data(self):
        from api.v1.serializers.message_serializers import SendEmailSerializer
        s = SendEmailSerializer(data=self._valid_data())
        assert s.is_valid(), s.errors

    def test_from_alias_remapped(self):
        from api.v1.serializers.message_serializers import SendEmailSerializer
        data = {
            "to": "recipient@example.com",
            "from": "sender@example.com",
            "subject": "Hello",
            "html_body": "<p>Hi</p>",
        }
        s = SendEmailSerializer(data=data)
        assert s.is_valid(), s.errors
        assert s.validated_data["from_address"] == "sender@example.com"

    def test_missing_body_and_template_fails(self):
        from api.v1.serializers.message_serializers import SendEmailSerializer
        data = {
            "to": "recipient@example.com",
            "from_address": "sender@example.com",
            "subject": "Hello",
        }
        s = SendEmailSerializer(data=data)
        assert not s.is_valid()

    def test_template_id_accepted_without_body(self):
        import uuid
        from api.v1.serializers.message_serializers import SendEmailSerializer
        data = {
            "to": "recipient@example.com",
            "from_address": "sender@example.com",
            "subject": "Hello",
            "template_id": str(uuid.uuid4()),
        }
        s = SendEmailSerializer(data=data)
        assert s.is_valid(), s.errors

    def test_send_at_optional(self):
        from api.v1.serializers.message_serializers import SendEmailSerializer
        data = self._valid_data(send_at="2030-01-01T10:00:00Z")
        s = SendEmailSerializer(data=data)
        assert s.is_valid(), s.errors
        assert s.validated_data["send_at"] is not None

    def test_stream_defaults_to_transactional(self):
        from api.v1.serializers.message_serializers import SendEmailSerializer
        s = SendEmailSerializer(data=self._valid_data())
        assert s.is_valid()
        assert s.validated_data["stream"] == "transactional"

    def test_invalid_to_email(self):
        from api.v1.serializers.message_serializers import SendEmailSerializer
        s = SendEmailSerializer(data=self._valid_data(to="not-an-email"))
        assert not s.is_valid()

    def test_subject_max_length(self):
        from api.v1.serializers.message_serializers import SendEmailSerializer
        s = SendEmailSerializer(data=self._valid_data(subject="x" * 999))
        assert not s.is_valid()


@pytest.mark.django_db
class TestMessageListSerializer:
    def test_fields(self, message):
        from api.v1.serializers.message_serializers import MessageListSerializer
        s = MessageListSerializer(message)
        data = s.data
        assert "id" in data
        assert "to_address" in data
        assert "from_address" in data
        assert "subject" in data
        assert "status" in data
        assert "created_at" in data
        assert "html_body" not in data  # detail only


@pytest.mark.django_db
class TestMessageDetailSerializer:
    def test_includes_events(self, sent_message, open_event):
        from api.v1.serializers.message_serializers import MessageDetailSerializer
        s = MessageDetailSerializer(sent_message)
        data = s.data
        assert "events" in data
        assert len(data["events"]) == 1
        assert data["events"][0]["type"] == "open"

    def test_includes_html_body(self, sent_message):
        from api.v1.serializers.message_serializers import MessageDetailSerializer
        s = MessageDetailSerializer(sent_message)
        assert "html_body" in s.data

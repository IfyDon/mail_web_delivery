"""Serializers for suppression-list management (bounces, complaints, unsubscribes)."""
from rest_framework import serializers

from .models import Bounce, Complaint, Unsubscribe


class BounceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bounce
        fields = ["id", "email", "reason", "smtp_code", "created_at"]
        read_only_fields = ["id", "created_at"]


class ComplaintSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint
        fields = ["id", "email", "feedback_type", "created_at"]
        read_only_fields = ["id", "created_at"]


class UnsubscribeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unsubscribe
        fields = ["id", "email", "source", "created_at"]
        read_only_fields = ["id", "token", "created_at"]


class SuppressionAddSerializer(serializers.Serializer):
    """Add an email to the suppression list manually."""

    email = serializers.EmailField()
    type = serializers.ChoiceField(choices=["bounce", "complaint", "unsubscribe", "manual"])
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class DeleteSuppressionSerializer(serializers.Serializer):
    """Bulk-remove emails from all suppression lists."""

    emails = serializers.ListField(
        child=serializers.EmailField(),
        min_length=1,
        max_length=100,
    )

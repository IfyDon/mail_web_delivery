"""Serializers for domain management."""
from rest_framework import serializers
from .models import Domain


class DomainSerializer(serializers.ModelSerializer):
    """Serializer for domain CRUD operations."""

    is_fully_verified = serializers.ReadOnlyField()
    dns_instructions = serializers.SerializerMethodField()

    class Meta:
        """Meta options for DomainSerializer."""

        model = Domain
        fields = [
            'id', 'domain', 'verification_status',
            'spf_verified', 'dkim_verified', 'dmarc_verified',
            'is_fully_verified', 'dkim_selector',
            'created_at', 'verified_at', 'last_checked_at',
            'dns_instructions'
        ]
        read_only_fields = [
            'id', 'verification_status',
            'spf_verified', 'dkim_verified', 'dmarc_verified',
            'created_at', 'verified_at', 'last_checked_at'
        ]

    def get_dns_instructions(self, obj):
        """Get DNS configuration instructions."""
        return obj.get_dns_instructions()


class DomainVerificationSerializer(serializers.Serializer):
    """Serializer for triggering domain verification."""

    domain_id = serializers.IntegerField()

    def validate_domain_id(self, value):
        """Validate that domain exists."""
        try:
            Domain.objects.get(id=value)
        except Domain.DoesNotExist as exc:
            raise serializers.ValidationError("Domain not found.") from exc
        return value


class DomainDKIMGenerateSerializer(serializers.Serializer):
    """Serializer for generating DKIM keys."""

    domain_id = serializers.IntegerField()

    def validate_domain_id(self, value):
        """Validate that domain exists."""
        try:
            Domain.objects.get(id=value)
        except Domain.DoesNotExist as exc:
            raise serializers.ValidationError("Domain not found.") from exc
        return value


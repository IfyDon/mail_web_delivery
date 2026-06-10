# Serializers for API key management, user quotas
from rest_framework import serializers
from .models import APIKey, Quota, CustomUser
import hashlib


class APIKeySerializer(serializers.ModelSerializer):
    """Serializer for API keys - never exposes the raw key after creation."""
    class Meta:
        model = APIKey
        fields = ['id', 'name', 'prefix', 'rate_limit', 'is_active', 'created_at', 'last_used_at']
        read_only_fields = ['id', 'prefix', 'created_at', 'last_used_at']


class APIKeyCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new API keys - returns the full key once."""
    key = serializers.SerializerMethodField()

    class Meta:
        model = APIKey
        fields = ['id', 'name', 'prefix', 'rate_limit', 'is_active', 'created_at', 'key']
        read_only_fields = ['id', 'prefix', 'is_active', 'created_at', 'key']

    def create(self, validated_data):
        user = self.context['request'].user
        full_key, prefix, hashed_key = APIKey.generate_key()
        
        api_key = APIKey.objects.create(
            user=user,
            prefix=prefix,
            hashed_key=hashed_key,
            name=validated_data['name'],
            rate_limit=validated_data.get('rate_limit', 1000)
        )
        self.full_key = full_key
        return api_key

    def get_key(self, obj):
        return getattr(self, 'full_key', None)


class QuotaSerializer(serializers.ModelSerializer):
    """Serializer for user quota tracking."""
    usage_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Quota
        fields = ['emails_sent_this_month', 'monthly_limit', 'reset_date', 'usage_percentage']
        read_only_fields = fields

    def get_usage_percentage(self, obj):
        if obj.monthly_limit == 0:
            return 0
        return round((obj.emails_sent_this_month / obj.monthly_limit) * 100, 2)


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profile information."""
    quota = QuotaSerializer(read_only=True)

    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'is_verified', 'created_at', 'quota']
        read_only_fields = ['id', 'created_at', 'quota']

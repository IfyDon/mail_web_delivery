# Serializers: RegisterSerializer, LoginSerializer, TokenSerializer, TwoFactorSerializer
from rest_framework import serializers
from django.contrib.auth import authenticate
from apps.accounts.models import CustomUser


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = CustomUser
        fields = ['email', 'first_name', 'last_name', 'password', 'password_confirm']

    def validate(self, data):
        if data['password'] != data.pop('password_confirm'):
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return data

    def create(self, validated_data):
        # Quota is provisioned by apps.accounts.signals.create_quota_for_new_user
        # on CustomUser's post_save — not here, so every creation path gets one.
        return CustomUser.objects.create_user(
            email=validated_data['email'],
            username=validated_data['email'],  # Use email as username
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
        )


class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    user = serializers.SerializerMethodField(read_only=True)

    def validate(self, data):
        user = authenticate(username=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        data['user'] = user
        return data

    def get_user(self, obj):
        from apps.accounts.serializers import UserSerializer
        return UserSerializer(obj['user']).data


class TokenSerializer(serializers.Serializer):
    """Serializer for session token (after successful login)."""
    token = serializers.CharField(read_only=True)
    user = serializers.SerializerMethodField(read_only=True)

    def get_user(self, obj):
        from apps.accounts.serializers import UserSerializer
        return UserSerializer(obj['user']).data


class TwoFactorSerializer(serializers.Serializer):
    """Serializer for 2FA setup and verification."""
    token = serializers.CharField(required=False)
    totp_code = serializers.CharField(write_only=True)

    def validate_totp_code(self, value):
        if not value.isdigit() or len(value) != 6:
            raise serializers.ValidationError("TOTP code must be 6 digits.")
        return value

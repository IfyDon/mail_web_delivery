from django.shortcuts import render
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django_otp.decorators import otp_required
from django_otp.plugins.otp_totp.models import TOTPDevice
from apps.accounts.models import CustomUser
from .serializers import RegisterSerializer, LoginSerializer, TokenSerializer, TwoFactorSerializer


class AuthenticationViewSet(viewsets.ViewSet):
    """Authentication endpoints: signup, login, 2FA."""
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['post'])
    def register(self, request):
        """Register a new user."""
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            from apps.accounts.serializers import UserSerializer
            return Response(
                {
                    'message': 'User registered successfully.',
                    'token': token.key,
                    'user': UserSerializer(user).data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=['get', 'patch', 'delete'],
        permission_classes=[permissions.IsAuthenticated],
    )
    def me(self, request):
        """Return, update, or delete the authenticated user's profile."""
        from apps.accounts.serializers import UserSerializer

        if request.method == 'DELETE':
            user = request.user
            Token.objects.filter(user=user).delete()
            user.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        if request.method == 'PATCH':
            allowed = {'first_name', 'last_name'}
            fields_to_update = [f for f in allowed if f in request.data]
            if fields_to_update:
                for field in fields_to_update:
                    setattr(request.user, field, request.data[field])
                request.user.save(update_fields=fields_to_update)
            return Response(UserSerializer(request.user).data)

        return Response(UserSerializer(request.user).data)

    @action(detail=False, methods=['post'])
    def login(self, request):
        """Login user and return session token."""
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)
            return Response(
                {
                    'token': token.key,
                    'user': serializer.data['user']
                },
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def logout(self, request):
        """Logout user by deleting token."""
        try:
            Token.objects.get(user=request.user).delete()
        except Token.DoesNotExist:
            pass
        return Response({'message': 'Logged out successfully.'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def setup_2fa(self, request):
        """Setup TOTP 2FA for user."""
        user = request.user
        device, created = TOTPDevice.objects.get_or_create(
            user=user,
            name='default',
            defaults={'confirmed': False}
        )
        
        if created or not device.confirmed:
            qr_code_url = device.config_url
            return Response(
                {
                    'message': '2FA setup initiated. Scan QR code with authenticator app.',
                    'qr_code': qr_code_url,
                    'device_id': device.id
                },
                status=status.HTTP_200_OK
            )
        
        return Response(
            {'message': '2FA is already enabled.'},
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def confirm_2fa(self, request):
        """Confirm TOTP code to enable 2FA."""
        serializer = TwoFactorSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        totp_code = serializer.validated_data['totp_code']
        device = TOTPDevice.objects.get(user=request.user, name='default')
        
        if device.verify_token(totp_code):
            device.confirmed = True
            device.save()
            return Response(
                {'message': '2FA enabled successfully.'},
                status=status.HTTP_200_OK
            )
        
        return Response(
            {'error': 'Invalid TOTP code.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def disable_2fa(self, request):
        """Disable TOTP 2FA."""
        TOTPDevice.objects.filter(user=request.user, name='default').delete()
        return Response(
            {'message': '2FA disabled.'},
            status=status.HTTP_200_OK
        )

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

    @action(detail=False, methods=['post'], url_path='2fa/setup',
            permission_classes=[permissions.IsAuthenticated])
    def setup_2fa(self, request):
        """Initiate TOTP 2FA setup. Returns a base64-encoded QR code image."""
        import base64
        import io
        import qrcode

        user = request.user
        device, _ = TOTPDevice.objects.get_or_create(
            user=user,
            name='default',
            defaults={'confirmed': False},
        )
        if device.confirmed:
            return Response({'message': '2FA is already enabled.'}, status=status.HTTP_200_OK)

        # Reset unconfirmed device so a fresh key is generated each time setup is triggered
        if not device.confirmed:
            device.delete()
            device = TOTPDevice.objects.create(user=user, name='default', confirmed=False)

        # Generate QR code image as a data URI
        img = qrcode.make(device.config_url)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        qr_data = base64.b64encode(buf.getvalue()).decode()
        qr_url = f"data:image/png;base64,{qr_data}"

        return Response({
            'message': '2FA setup initiated. Scan the QR code with your authenticator app.',
            'qr_url': qr_url,
            'device_id': device.id,
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='2fa/verify',
            permission_classes=[permissions.IsAuthenticated])
    def confirm_2fa(self, request):
        """Verify a TOTP code and activate 2FA."""
        code = request.data.get('code', '').strip()
        if not code:
            return Response({'error': 'code is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            device = TOTPDevice.objects.get(user=request.user, name='default')
        except TOTPDevice.DoesNotExist:
            return Response({'error': 'No 2FA setup in progress.'}, status=status.HTTP_400_BAD_REQUEST)

        if device.verify_token(code):
            device.confirmed = True
            device.save()
            return Response({'message': '2FA enabled successfully.'}, status=status.HTTP_200_OK)

        return Response({'error': 'Invalid TOTP code. Try again.'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='2fa/disable',
            permission_classes=[permissions.IsAuthenticated])
    def disable_2fa(self, request):
        """Disable TOTP 2FA for the authenticated user."""
        TOTPDevice.objects.filter(user=request.user, name='default').delete()
        return Response({'message': '2FA disabled.'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='password/change',
            permission_classes=[permissions.IsAuthenticated])
    def change_password(self, request):
        """Change password for authenticated user. Requires current password."""
        current_password = request.data.get('current_password', '')
        new_password = request.data.get('new_password', '')

        if not current_password or not new_password:
            return Response(
                {'detail': 'current_password and new_password are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not request.user.check_password(current_password):
            return Response(
                {'detail': 'Current password is incorrect.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(new_password) < 8:
            return Response(
                {'detail': 'New password must be at least 8 characters.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.set_password(new_password)
        request.user.save(update_fields=['password'])
        # Keep the user's token valid after password change
        from rest_framework.authtoken.models import Token
        Token.objects.filter(user=request.user).delete()
        token, _ = Token.objects.get_or_create(user=request.user)
        return Response({'detail': 'Password updated successfully.', 'token': token.key})

    @action(detail=False, methods=['post'], url_path='password-reset')
    def password_reset(self, request):
        """Send a password-reset email. Always returns 200 to avoid email enumeration."""
        from django.conf import settings as django_settings
        from django.contrib.auth.tokens import default_token_generator
        from django.core.mail import send_mail
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        email = request.data.get('email', '').strip().lower()
        try:
            user = CustomUser.objects.get(email__iexact=email)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            frontend_url = getattr(django_settings, 'FRONTEND_BASE_URL', 'http://localhost:3000')
            reset_url = f"{frontend_url}/reset-password?uid={uid}&token={token}"
            send_mail(
                subject='Reset your WebMail password',
                message=(
                    f"Hi {user.email},\n\n"
                    f"Click the link below to reset your password. "
                    f"This link expires in 1 hour.\n\n{reset_url}\n\n"
                    f"If you did not request a reset, ignore this email."
                ),
                from_email='noreply@webmail.dev',
                recipient_list=[user.email],
                fail_silently=True,
            )
        except CustomUser.DoesNotExist:
            pass
        return Response(
            {'message': 'If that email is registered, a reset link has been sent.'},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['post'], url_path='password-reset/confirm')
    def password_reset_confirm(self, request):
        """Validate uid+token and set the new password."""
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_str
        from django.utils.http import urlsafe_base64_decode

        uid = request.data.get('uid', '')
        token = request.data.get('token', '')
        new_password = request.data.get('new_password', '')

        if not uid or not token or not new_password:
            return Response(
                {'error': 'uid, token, and new_password are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(new_password) < 8:
            return Response(
                {'error': 'Password must be at least 8 characters.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user_pk = force_str(urlsafe_base64_decode(uid))
            user = CustomUser.objects.get(pk=user_pk)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            return Response({'error': 'Invalid reset link.'}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return Response(
                {'error': 'This reset link is invalid or has expired.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=['password'])
        return Response({'message': 'Password updated successfully.'}, status=status.HTTP_200_OK)

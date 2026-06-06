from django.shortcuts import render
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import APIKey, Quota, CustomUser
from .serializers import APIKeySerializer, APIKeyCreateSerializer, QuotaSerializer, UserSerializer


class APIKeyViewSet(viewsets.ModelViewSet):
    """ViewSet for managing API keys."""
    serializer_class = APIKeySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Return only the current user's API keys."""
        return APIKey.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return APIKeyCreateSerializer
        return APIKeySerializer
    
    def perform_create(self, serializer):
        """Automatically set the user to the authenticated user."""
        # serializer.create accesses request via serializer.context, so no args required
        serializer.save()

    @action(detail=True, methods=['post'])
    def rotate(self, request, pk=None):
        """Rotate (replace) an API key: create a new key and deactivate the old one.

        Returns the full new key only once in the response.
        """
        api_key = self.get_object()
        if api_key.user != request.user:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Generate a new key and create a new APIKey record
        full_key, prefix, hashed_key = APIKey.generate_key()
        new_key = APIKey.objects.create(
            user=request.user,
            name=api_key.name,
            prefix=prefix,
            hashed_key=hashed_key,
            rate_limit=api_key.rate_limit,
            is_active=True,
        )

        # Deactivate the old key
        api_key.is_active = False
        api_key.save(update_fields=['is_active'])

        serializer = APIKeySerializer(new_key)
        return Response({'new_key': full_key, 'key': serializer.data}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """Revoke (deactivate) an API key."""
        api_key = self.get_object()
        if api_key.user != request.user:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        api_key.is_active = False
        api_key.save(update_fields=['is_active'])
        return Response({'message': 'API key revoked.'}, status=status.HTTP_200_OK)


class QuotaViewSet(viewsets.ViewSet):
    """ViewSet for viewing user quota."""
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current user's quota."""
        quota = Quota.objects.get(user=request.user)
        serializer = QuotaSerializer(quota)
        return Response(serializer.data)


class UserProfileViewSet(viewsets.ViewSet):
    """ViewSet for user profile management."""
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get', 'put', 'patch'])
    def me(self, request):
        """Get or update current user's profile."""
        if request.method == 'GET':
            serializer = UserSerializer(request.user)
            return Response(serializer.data)
        else:  # PUT or PATCH
            serializer = UserSerializer(request.user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

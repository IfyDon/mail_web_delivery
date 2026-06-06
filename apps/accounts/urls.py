from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import APIKeyViewSet, QuotaViewSet, UserProfileViewSet

router = DefaultRouter()
router.register(r'api-keys', APIKeyViewSet, basename='api-keys')

urlpatterns = [
	path('', include(router.urls)),
	path('quota/', QuotaViewSet.as_view({'get': 'current'}), name='quota-current'),
	path('me/', UserProfileViewSet.as_view({'get': 'me', 'put': 'me', 'patch': 'me'}), name='user-me'),
]

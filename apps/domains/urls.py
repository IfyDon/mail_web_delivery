"""URL patterns for domain management."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DomainViewSet

router = DefaultRouter()
router.register(r'', DomainViewSet, basename='domains')

urlpatterns = [
    path('', include(router.urls)),
]


"""URL patterns for email templates."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TemplateViewSet

router = DefaultRouter()
router.register(r'', TemplateViewSet, basename='templates')

urlpatterns = [
	path('', include(router.urls)),
]

"""
Main URL configuration for Web Mail project.
Routes:
  /api/v1/        → REST API endpoints
  /admin/         → Django admin
  /tracking/      → Email tracking (opens/clicks)
  /               → Marketing site and dashboard
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Versioned API
    path('api/v1/', include('api.v1.urls')),

    # Email tracking (lightweight endpoints)
    path('tracking/', include('tracking.urls')),

    # One-click unsubscribe (no auth — linked from every email)
    path('', include('apps.suppressions.urls')),

    # Cookie consent (django-cookie-consent)
    path('cookies/', include('cookie_consent.urls')),

    # Marketing site and dashboard
    path('', include('web.urls')),
]

# Debug Toolbar (development only)
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns

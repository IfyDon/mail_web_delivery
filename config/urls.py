"""
Main URL configuration for Web Mail project.
Routes:
  /api/        → API root / versions
  /api/v1/     → REST API endpoints
  /admin/      → Django admin
  /tracking/   → Email tracking (opens/clicks)
  /            → Marketing site and dashboard
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def api_root(request):
    """API root endpoint."""
    return Response({
        'status': 'ok',
        'message': 'Web Mail API',
        'versions': {
            'v1': {
                'status': 'active',
                'url': request.build_absolute_uri('/api/v1/'),
                'docs': request.build_absolute_uri('/api/docs/'),
            }
        },
        'documentation': request.build_absolute_uri('/api/docs/'),
        'schema': request.build_absolute_uri('/api/schema/'),
    })

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # API root
    path('api/', api_root, name='api-root'),

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

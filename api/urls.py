"""API root URL router. Mounts versioned sub-routers."""
from django.urls import path, include

urlpatterns = [
    path('v1/', include('api.v1.urls')),
]

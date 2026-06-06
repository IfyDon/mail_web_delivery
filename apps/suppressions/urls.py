"""Web URL patterns for the public-facing unsubscribe landing page."""
from django.urls import path
from .views import unsubscribe_view

urlpatterns = [
    path("unsubscribe/<str:token>/", unsubscribe_view, name="unsubscribe"),
]

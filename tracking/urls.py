from django.urls import path

from tracking.views import ClickTrackingView, OpenTrackingView

urlpatterns = [
    path("open/<str:token>/", OpenTrackingView.as_view(), name="track-open"),
    path("click/<str:token>/", ClickTrackingView.as_view(), name="track-click"),
]

from django.urls import path

from .views import StreamDetailView, StreamListCreateView

urlpatterns = [
    path('', StreamListCreateView.as_view(), name='stream-list'),
    path('<slug:slug>/', StreamDetailView.as_view(), name='stream-detail'),
]

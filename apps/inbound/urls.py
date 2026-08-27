from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import InboundMessageDetailView, InboundMessageListView, InboundRouteViewSet

router = DefaultRouter()
router.register(r'routes', InboundRouteViewSet, basename='inbound-routes')

urlpatterns = [
    path('messages/', InboundMessageListView.as_view(), name='inbound-message-list'),
    path('messages/<int:pk>/', InboundMessageDetailView.as_view(), name='inbound-message-detail'),
    path('', include(router.urls)),
]

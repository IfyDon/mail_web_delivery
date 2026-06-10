"""GET /api/v1/contacts/engagement/ — paginated contact engagement list."""
from rest_framework.generics import ListAPIView

from apps.analytics.models import ContactEngagement
from api.v1.serializers.contact_serializers import ContactEngagementSerializer


class ContactEngagementView(ListAPIView):
    """Return the authenticated user's contacts sorted by engagement score (desc)."""

    serializer_class = ContactEngagementSerializer

    def get_queryset(self):
        return (
            ContactEngagement.objects
            .filter(user=self.request.user)
            .order_by("-score")
        )

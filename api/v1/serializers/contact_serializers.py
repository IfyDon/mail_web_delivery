from rest_framework import serializers
from apps.analytics.models import ContactEngagement


class ContactEngagementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactEngagement
        fields = [
            "email",
            "score",
            "open_count",
            "click_count",
            "bounce_count",
            "complaint_count",
            "last_open",
            "last_click",
            "last_event",
            "updated_at",
        ]

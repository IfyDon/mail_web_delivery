"""Serializers for stats API responses."""
from rest_framework import serializers


class DailyStatSerializer(serializers.Serializer):
    date = serializers.DateField()
    sent = serializers.IntegerField()
    delivered = serializers.IntegerField()
    opened = serializers.IntegerField()
    clicked = serializers.IntegerField()
    bounced = serializers.IntegerField()
    complained = serializers.IntegerField()


class StatsResponseSerializer(serializers.Serializer):
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    stream = serializers.CharField(allow_null=True)
    totals = DailyStatSerializer()
    by_day = DailyStatSerializer(many=True)

from rest_framework import serializers

from .models import Stream


class StreamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stream
        fields = ['id', 'name', 'slug', 'description', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_slug(self, value):
        request = self.context.get('request')
        qs = Stream.objects.filter(user=request.user, slug=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('You already have a stream with this slug.')
        return value

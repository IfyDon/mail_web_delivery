"""Serializers for inbound routing rules and received mail."""
from rest_framework import serializers

from apps.domains.models import Domain

from .models import InboundAttachment, InboundMessage, InboundRoute


class InboundRouteSerializer(serializers.ModelSerializer):
    address = serializers.ReadOnlyField()
    domain = serializers.PrimaryKeyRelatedField(queryset=Domain.objects.none())
    # Declared explicitly (not left to ModelSerializer inference): the
    # auto-generated UniqueTogetherValidator for ('domain', 'local_part')
    # otherwise forces this required=True, overriding the model's blank=True.
    local_part = serializers.CharField(max_length=64, required=False, allow_blank=True, default='')

    class Meta:
        model = InboundRoute
        fields = [
            'id', 'domain', 'match_type', 'local_part',
            'address', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request is not None:
            self.fields['domain'].queryset = Domain.objects.filter(
                user=request.user, verification_status='verified',
            )

    def validate(self, attrs):
        match_type = attrs.get('match_type', getattr(self.instance, 'match_type', InboundRoute.MATCH_WILDCARD))
        local_part = attrs.get('local_part', getattr(self.instance, 'local_part', ''))
        if match_type == InboundRoute.MATCH_EXACT and not local_part:
            raise serializers.ValidationError(
                {'local_part': 'Required when match_type is "exact".'}
            )
        if match_type == InboundRoute.MATCH_WILDCARD and local_part:
            raise serializers.ValidationError(
                {'local_part': 'Must be blank when match_type is "wildcard".'}
            )
        if local_part and '@' in local_part:
            raise serializers.ValidationError(
                {'local_part': 'Provide only the part before "@" (e.g. "support").'}
            )
        return attrs


class InboundAttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = InboundAttachment
        fields = ['id', 'filename', 'content_type', 'size', 'url']

    def get_url(self, obj):
        request = self.context.get('request')
        if not obj.file:
            return None
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url


class InboundMessageListSerializer(serializers.ModelSerializer):
    route_address = serializers.CharField(source='route.address', read_only=True, default=None)

    class Meta:
        model = InboundMessage
        fields = [
            'id', 'from_address', 'to_address', 'subject',
            'status', 'route_address', 'received_at',
        ]


class InboundMessageDetailSerializer(serializers.ModelSerializer):
    attachments = InboundAttachmentSerializer(many=True, read_only=True)
    route_address = serializers.CharField(source='route.address', read_only=True, default=None)

    class Meta:
        model = InboundMessage
        fields = [
            'id', 'from_address', 'to_address', 'subject',
            'text_body', 'html_body', 'headers',
            'spam_verdict', 'virus_verdict', 'status',
            'route_address', 'received_at', 'attachments',
        ]

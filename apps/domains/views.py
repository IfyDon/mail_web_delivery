"""Views for domain management."""
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from core.utils.dns_utils import verify_domain_dns
from .models import Domain
from .serializers import DomainSerializer


class DomainViewSet(viewsets.ModelViewSet):
    """ViewSet for managing sending domains."""

    serializer_class = DomainSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return only current user's domains."""
        return Domain.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Save domain and immediately generate DKIM key pair."""
        domain = serializer.save(user=self.request.user)
        domain.generate_dkim_keys()

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify domain DNS records."""
        domain = self.get_object()
        if domain.user != request.user:
            return Response(
                {'detail': 'Not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check all DNS records
        results = verify_domain_dns(domain.domain)
        spf_result = results['spf']
        dkim_result = results['dkim']
        dmarc_result = results['dmarc']

        # Update domain verification status
        domain.spf_verified = spf_result.is_valid
        domain.dkim_verified = dkim_result.is_valid
        domain.dmarc_verified = dmarc_result.is_valid
        domain.last_checked_at = timezone.now()

        # Update overall verification status
        if domain.is_fully_verified:
            domain.verification_status = 'verified'
            domain.verified_at = timezone.now()
        elif domain.spf_verified or domain.dkim_verified or domain.dmarc_verified:
            domain.verification_status = 'pending'
        else:
            domain.verification_status = 'failed'

        domain.save()

        return Response({
            'domain': domain.domain,
            'verification_status': domain.verification_status,
            'spf_verified': domain.spf_verified,
            'spf_error': spf_result.error,
            'dkim_verified': domain.dkim_verified,
            'dkim_error': dkim_result.error,
            'dmarc_verified': domain.dmarc_verified,
            'dmarc_error': dmarc_result.error,
            'dns_instructions': domain.get_dns_instructions()
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def generate_dkim(self, request, pk=None):
        """Generate DKIM key pair for domain."""
        domain = self.get_object()
        if domain.user != request.user:
            return Response(
                {'detail': 'Not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        private_key, public_key = domain.generate_dkim_keys()

        return Response({
            'domain': domain.domain,
            'dkim_selector': domain.dkim_selector,
            'dns_instructions': domain.get_dns_instructions(),
            'private_key': private_key,
            'public_key': public_key
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def verified(self, request):
        """List only verified domains."""
        domains = self.get_queryset().filter(
            verification_status='verified'
        )
        serializer = self.get_serializer(domains, many=True)
        return Response(serializer.data)


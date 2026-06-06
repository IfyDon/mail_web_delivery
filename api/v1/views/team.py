"""Team member management endpoints.

GET    /api/v1/team/         - list members + pending invites (owner/admin)
POST   /api/v1/team/invite/  - send invitation email
PATCH  /api/v1/team/{id}/    - change member role
DELETE /api/v1/team/{id}/    - remove member or cancel invite
"""
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.models import TeamMember
from services.team_service import invite_member, remove_member


class TeamMemberSerializer(serializers.ModelSerializer):
    is_pending = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = TeamMember
        fields = ['id', 'email', 'role', 'invited_at', 'accepted_at', 'is_pending', 'is_expired']
        read_only_fields = ['id', 'invited_at', 'accepted_at']


class InviteSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=['admin', 'viewer'])


@extend_schema(tags=["Team"])
class TeamListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: TeamMemberSerializer(many=True)}, summary="List team members")
    def get(self, request):
        members = TeamMember.objects.filter(account_owner=request.user)
        return Response(TeamMemberSerializer(members, many=True).data)

    @extend_schema(request=InviteSerializer, responses={201: TeamMemberSerializer}, summary="Invite a team member")
    def post(self, request):
        serializer = InviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        role = serializer.validated_data['role']

        if email.lower() == request.user.email.lower():
            return Response({'detail': 'Cannot invite yourself.'}, status=status.HTTP_400_BAD_REQUEST)

        member = invite_member(request.user, email, role)
        return Response(TeamMemberSerializer(member).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Team"])
class TeamDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, request, pk):
        try:
            return TeamMember.objects.get(pk=pk, account_owner=request.user)
        except TeamMember.DoesNotExist:
            return None

    @extend_schema(responses={200: TeamMemberSerializer}, summary="Change a member's role")
    def patch(self, request, pk):
        member = self._get(request, pk)
        if member is None:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        role = request.data.get('role')
        if role not in ('admin', 'viewer'):
            return Response({'detail': 'role must be admin or viewer.'}, status=status.HTTP_400_BAD_REQUEST)

        member.role = role
        member.save()
        return Response(TeamMemberSerializer(member).data)

    @extend_schema(responses={204: None}, summary="Remove member or cancel invite")
    def delete(self, request, pk):
        removed = remove_member(request.user, pk)
        if not removed:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

"""Server-rendered dashboard views for team member management."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from apps.authentication.models import TeamMember
from services.team_service import accept_invite, invite_member, remove_member


class TeamView(LoginRequiredMixin, View):
    login_url = "/login/"
    template_name = "dashboard/team.html"

    def get(self, request):
        members = TeamMember.objects.filter(account_owner=request.user)
        return render(request, self.template_name, {
            "members": members,
            "role_choices": TeamMember.ROLE_CHOICES,
        })

    def post(self, request):
        email = request.POST.get("email", "").strip().lower()
        role = request.POST.get("role", TeamMember.ROLE_VIEWER)
        if not email:
            messages.error(request, "Enter an email address.")
            return redirect("team")
        if role not in dict(TeamMember.ROLE_CHOICES):
            role = TeamMember.ROLE_VIEWER
        if email == request.user.email.lower():
            messages.error(request, "You can't invite yourself.")
            return redirect("team")

        invite_member(request.user, email, role)
        messages.success(request, f"Invitation sent to {email}.")
        return redirect("team")


class TeamRoleChangeView(LoginRequiredMixin, View):
    login_url = "/login/"

    def post(self, request, pk):
        role = request.POST.get("role")
        if role not in dict(TeamMember.ROLE_CHOICES):
            messages.error(request, "Invalid role.")
            return redirect("team")
        updated = TeamMember.objects.filter(pk=pk, account_owner=request.user).update(role=role)
        if updated:
            messages.success(request, "Role updated.")
        return redirect("team")


class TeamResendView(LoginRequiredMixin, View):
    login_url = "/login/"

    def post(self, request, pk):
        member = TeamMember.objects.filter(pk=pk, account_owner=request.user).first()
        if member:
            invite_member(request.user, member.email, member.role)
            messages.success(request, f"Invitation resent to {member.email}.")
        return redirect("team")


class TeamRemoveView(LoginRequiredMixin, View):
    login_url = "/login/"

    def post(self, request, pk):
        if remove_member(request.user, pk):
            messages.success(request, "Team member removed.")
        return redirect("team")


class AcceptInviteView(LoginRequiredMixin, View):
    login_url = "/login/"

    def get(self, request, token):
        member = accept_invite(token, request.user)
        if member:
            messages.success(
                request,
                f"You've joined {member.account_owner.email}'s team as {member.get_role_display()}.",
            )
        else:
            messages.error(request, "This invitation link is invalid or has expired.")
        return redirect("dashboard")

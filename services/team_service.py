"""Team member invitation and management service."""
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from apps.authentication.models import TeamMember


def invite_member(owner, email: str, role: str) -> TeamMember:
    """Create or re-send a team invitation. Returns the TeamMember record."""
    token = TeamMember.generate_invite_token()
    member, created = TeamMember.objects.get_or_create(
        account_owner=owner,
        email=email.lower(),
        defaults={'role': role, 'invite_token': token},
    )
    if not created:
        # Resend: refresh token and clear any prior acceptance
        member.role = role
        member.invite_token = token
        member.accepted_at = None
        member.save()

    accept_url = f"{settings.BASE_URL}/accept-invite/{token}/"
    send_mail(
        subject=f"You've been invited to join {owner.email}'s WebMail account",
        message=(
            f"You've been invited as {role}.\n\n"
            f"Accept the invitation here: {accept_url}\n\n"
            "This link expires in 48 hours."
        ),
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@webmail.io'),
        recipient_list=[email],
        fail_silently=True,
    )
    return member


def accept_invite(token: str, user) -> TeamMember | None:
    """Accept an invitation and link it to `user`. Returns None if invalid or expired."""
    try:
        tm = TeamMember.objects.get(invite_token=token, accepted_at__isnull=True)
    except TeamMember.DoesNotExist:
        return None

    if timezone.now() > tm.invited_at + timedelta(hours=48):
        return None

    tm.member = user
    tm.accepted_at = timezone.now()
    tm.save()
    return tm


def remove_member(owner, team_member_id: int) -> bool:
    """Remove a team member (or cancel a pending invite). Returns True if deleted."""
    deleted, _ = TeamMember.objects.filter(
        pk=team_member_id,
        account_owner=owner,
    ).delete()
    return deleted > 0

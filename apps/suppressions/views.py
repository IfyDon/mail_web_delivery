"""Public unsubscribe landing page — no authentication required."""

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from tracking.tokens import verify_unsubscribe_token

User = get_user_model()


@require_http_methods(["GET", "POST"])
def unsubscribe_view(request, token: str):
    """One-click unsubscribe endpoint.

    GET  /unsubscribe/<token>/  — render confirmation page
    POST /unsubscribe/<token>/  — add suppression, render success page
    """
    data = verify_unsubscribe_token(token)
    if not data:
        return HttpResponse("This unsubscribe link is invalid or has expired.", status=410)

    email = data["email"]
    user_id = data["user_id"]

    if request.method == "POST":
        try:
            user = User.objects.get(pk=user_id)
            from services.suppression_service import add_suppression
            from apps.suppressions.models import Suppression
            add_suppression(user, email, Suppression.REASON_UNSUBSCRIBE)
        except User.DoesNotExist:
            pass  # user deleted — suppression no longer meaningful
        return render(request, "landing/unsubscribe_confirm.html", {"email": email})

    return render(request, "landing/unsubscribe.html", {"email": email, "token": token})

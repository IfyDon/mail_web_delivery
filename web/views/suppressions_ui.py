"""Server-rendered dashboard views for the suppression list."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.suppressions.models import Suppression
from services.suppression_service import add_suppression


class SuppressionsView(LoginRequiredMixin, View):
    login_url = "/login/"
    template_name = "dashboard/suppressions.html"

    def get(self, request):
        reason_filter = request.GET.get("reason", "")
        qs = Suppression.objects.filter(user=request.user)
        total = qs.count()
        if reason_filter:
            qs = qs.filter(reason=reason_filter)

        return render(request, self.template_name, {
            "suppressions": qs[:200],
            "total": total,
            "reason_filter": reason_filter,
            "reason_choices": Suppression.REASON_CHOICES,
        })

    def post(self, request):
        email = request.POST.get("email", "").strip()
        if not email:
            messages.error(request, "Enter an email address.")
            return redirect("suppressions")

        add_suppression(request.user, email, Suppression.REASON_MANUAL)
        messages.success(request, f"Suppressed {email}.")
        return redirect("suppressions")


class SuppressionRemoveView(LoginRequiredMixin, View):
    login_url = "/login/"

    def post(self, request, pk):
        suppression = get_object_or_404(Suppression, pk=pk, user=request.user)
        email = suppression.email
        suppression.delete()
        messages.success(request, f"Removed {email} from the suppression list.")
        return redirect("suppressions")

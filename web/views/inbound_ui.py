"""Server-rendered dashboard views for inbound email routing."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.domains.models import Domain
from apps.inbound.models import InboundMessage, InboundRoute


class InboundView(LoginRequiredMixin, View):
    login_url = "/login/"
    template_name = "dashboard/inbound.html"

    def get(self, request):
        routes = InboundRoute.objects.filter(user=request.user).select_related("domain")
        recent_messages = (
            InboundMessage.objects.filter(user=request.user)
            .select_related("route", "route__domain")
            .prefetch_related("attachments")[:50]
        )
        verified_domains = Domain.objects.filter(
            user=request.user, verification_status="verified",
        )
        return render(request, self.template_name, {
            "routes": routes,
            "recent_messages": recent_messages,
            "verified_domains": verified_domains,
        })

    def post(self, request):
        domain_id = request.POST.get("domain")
        match_type = request.POST.get("match_type", InboundRoute.MATCH_WILDCARD)
        local_part = request.POST.get("local_part", "").strip()

        domain = Domain.objects.filter(
            pk=domain_id, user=request.user, verification_status="verified",
        ).first()
        if domain is None:
            messages.error(request, "Choose a verified domain.")
            return redirect("inbound")

        if match_type == InboundRoute.MATCH_EXACT and not local_part:
            messages.error(request, 'An address (e.g. "support") is required for a single-address route.')
            return redirect("inbound")
        if match_type == InboundRoute.MATCH_WILDCARD:
            local_part = ""

        if InboundRoute.objects.filter(domain=domain, local_part=local_part).exists():
            messages.error(request, "A route for that address already exists.")
            return redirect("inbound")

        InboundRoute.objects.create(
            user=request.user, domain=domain, match_type=match_type, local_part=local_part,
        )
        messages.success(request, "Inbound route added.")
        return redirect("inbound")


class InboundRouteDeleteView(LoginRequiredMixin, View):
    login_url = "/login/"

    def post(self, request, pk):
        route = get_object_or_404(InboundRoute, pk=pk, user=request.user)
        route.delete()
        messages.success(request, "Inbound route removed.")
        return redirect("inbound")


class InboundMessageDetailView(LoginRequiredMixin, View):
    login_url = "/login/"
    template_name = "dashboard/inbound_message_detail.html"

    def get(self, request, pk):
        message = get_object_or_404(
            InboundMessage.objects.select_related("route", "route__domain").prefetch_related("attachments"),
            pk=pk, user=request.user,
        )
        return render(request, self.template_name, {"message": message})

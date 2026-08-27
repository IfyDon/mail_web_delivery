"""Server-rendered dashboard views for sending-domain management."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.domains.models import Domain
from services import dns_service


class DomainsView(LoginRequiredMixin, View):
    login_url = "/login/"
    template_name = "dashboard/domains.html"

    def get(self, request):
        domains = Domain.objects.filter(user=request.user)
        return render(request, self.template_name, {"domains": domains})

    def post(self, request):
        name = request.POST.get("domain", "").strip().lower().strip(".")
        if not name:
            messages.error(request, "Enter a domain name.")
            return redirect("domains")

        domain, created = Domain.objects.get_or_create(user=request.user, domain=name)
        if created:
            domain.generate_dkim_keys()
            messages.success(request, f'Added "{name}". Publish the DNS records below, then verify.')
        else:
            messages.info(request, f'"{name}" is already on your account.')
        return redirect("domains")


class DomainVerifyView(LoginRequiredMixin, View):
    login_url = "/login/"

    def post(self, request, pk):
        domain = get_object_or_404(Domain, pk=pk, user=request.user)
        result = dns_service.verify_domain(domain)
        if result["status"] == "verified":
            messages.success(request, f"{domain.domain} is fully verified.")
        else:
            missing = [k.upper() for k in ("spf", "dkim", "dmarc") if not result[k]]
            messages.warning(request, f'{domain.domain}: still missing {", ".join(missing)}.')
        return redirect("domains")


class DomainDeleteView(LoginRequiredMixin, View):
    login_url = "/login/"

    def post(self, request, pk):
        domain = get_object_or_404(Domain, pk=pk, user=request.user)
        name = domain.domain
        domain.delete()
        messages.success(request, f"Removed {name}.")
        return redirect("domains")

"""Server-rendered dashboard views for webhook endpoint configuration."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.webhooks.models import Webhook


class WebhooksView(LoginRequiredMixin, View):
    login_url = "/login/"
    template_name = "dashboard/webhooks.html"

    def get(self, request):
        webhooks = Webhook.objects.filter(user=request.user).prefetch_related("dispatch_logs")
        return render(request, self.template_name, {
            "webhooks": webhooks,
            "all_event_types": Webhook.ALL_EVENT_TYPES,
        })

    def post(self, request):
        url = request.POST.get("url", "").strip()
        event_types = request.POST.getlist("event_types") or list(Webhook.ALL_EVENT_TYPES)
        if not url:
            messages.error(request, "Enter an endpoint URL.")
            return redirect("webhooks")

        Webhook.objects.create(user=request.user, url=url, event_types=event_types)
        messages.success(request, f"Added webhook endpoint {url}.")
        return redirect("webhooks")


class WebhookDeleteView(LoginRequiredMixin, View):
    login_url = "/login/"

    def post(self, request, pk):
        webhook = get_object_or_404(Webhook, pk=pk, user=request.user)
        webhook.delete()
        messages.success(request, "Webhook endpoint removed.")
        return redirect("webhooks")

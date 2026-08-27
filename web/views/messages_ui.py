"""Server-rendered dashboard views for message history and detail."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView

from apps.email_messages.models import Message


class MessagesView(LoginRequiredMixin, TemplateView):
    login_url = "/login/"
    template_name = "dashboard/messages.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        status_filter = self.request.GET.get("status", "")

        qs = Message.objects.filter(user=self.request.user)
        if status_filter:
            qs = qs.filter(status=status_filter)

        ctx.update({
            "messages_list": list(qs[:100]),
            "status_filter": status_filter,
            "status_choices": Message.STATUS_CHOICES,
        })
        return ctx


class MessageDetailView(LoginRequiredMixin, TemplateView):
    login_url = "/login/"
    template_name = "dashboard/message_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        msg = get_object_or_404(
            Message.objects.select_related("domain", "template_version"),
            pk=kwargs["pk"], user=self.request.user,
        )
        ctx.update({
            "msg": msg,
            "events": msg.events.all(),
        })
        return ctx


class MessageResendView(LoginRequiredMixin, View):
    login_url = "/login/"

    def post(self, request, pk):
        msg = get_object_or_404(Message, pk=pk, user=request.user)
        if msg.status != Message.STATUS_PERMANENTLY_FAILED:
            messages.error(request, "Only permanently failed messages can be resent.")
            return redirect("message_detail", pk=pk)

        from workers.tasks.send_email import send_email_task

        msg.status = Message.STATUS_QUEUED
        msg.attempts = 0
        msg.save(update_fields=["status", "attempts", "updated_at"])
        send_email_task.delay(str(msg.pk))
        messages.success(request, "Message re-queued for delivery.")
        return redirect("message_detail", pk=pk)

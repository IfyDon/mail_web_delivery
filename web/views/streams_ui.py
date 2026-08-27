"""Server-rendered dashboard views for message stream management."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.views import View

from apps.email_messages.models import Message
from apps.streams.models import Stream


class StreamsView(LoginRequiredMixin, View):
    login_url = "/login/"
    template_name = "dashboard/streams.html"

    def get(self, request):
        streams = list(Stream.objects.filter(user=request.user))
        for stream in streams:
            msgs = Message.objects.filter(user=request.user, stream=stream.slug)
            sent = msgs.count()
            bounced = msgs.filter(status=Message.STATUS_PERMANENTLY_FAILED).count()
            stream.sent_count = sent
            stream.bounce_rate = round(bounced / sent * 100, 2) if sent else 0
        return render(request, self.template_name, {"streams": streams})

    def post(self, request):
        name = request.POST.get("name", "").strip()
        if not name:
            messages.error(request, "Enter a stream name.")
            return redirect("streams")

        base_slug = slugify(name) or "stream"
        slug = base_slug
        suffix = 1
        while Stream.objects.filter(user=request.user, slug=slug).exists():
            suffix += 1
            slug = f"{base_slug}-{suffix}"

        Stream.objects.create(
            user=request.user, name=name, slug=slug,
            description=request.POST.get("description", "").strip(),
        )
        messages.success(request, f'Created stream "{name}".')
        return redirect("streams")


class StreamArchiveView(LoginRequiredMixin, View):
    login_url = "/login/"

    def post(self, request, pk):
        stream = get_object_or_404(Stream, pk=pk, user=request.user)
        stream.is_active = not stream.is_active
        stream.save(update_fields=["is_active"])
        messages.success(
            request,
            f'{"Archived" if not stream.is_active else "Reactivated"} "{stream.name}".',
        )
        return redirect("streams")


class StreamDeleteView(LoginRequiredMixin, View):
    login_url = "/login/"

    def post(self, request, pk):
        stream = get_object_or_404(Stream, pk=pk, user=request.user)
        name = stream.name
        stream.delete()
        messages.success(request, f'Deleted stream "{name}".')
        return redirect("streams")

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView, View

from apps.accounts.models import APIKey


class APIKeyCreateView(LoginRequiredMixin, FormView):
    template_name = "dashboard/api_key_create.html"
    login_url = "/login/"

    def get(self, request, *args, **kwargs):
        return self.render_to_response({})

    def post(self, request, *args, **kwargs):
        name = request.POST.get("name", "").strip()
        if not name:
            return self.render_to_response({"error": "Key name is required.", "name": name})

        raw_key, prefix, hashed = APIKey.generate_key()
        APIKey.objects.create(
            user=request.user,
            name=name,
            prefix=prefix,
            hashed_key=hashed,
        )
        # Show the key once — it cannot be retrieved again
        return self.render_to_response({"created_key": raw_key, "key_name": name})


class APIKeyRevokeView(LoginRequiredMixin, View):
    login_url = "/login/"

    def post(self, request, pk, *args, **kwargs):
        key = get_object_or_404(APIKey, pk=pk, user=request.user)
        key.is_active = False
        key.save(update_fields=["is_active"])
        messages.success(request, f'API key "{key.name}" has been revoked.')
        return redirect("/dashboard/")

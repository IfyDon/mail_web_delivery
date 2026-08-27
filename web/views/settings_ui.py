"""Server-rendered dashboard views for account settings: password + 2FA."""
import base64
import io
import secrets

import qrcode
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views import View
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

_DEVICE_NAME = "default"
_BACKUP_DEVICE_NAME = "backup"


def _qr_data_uri(config_url: str) -> str:
    img = qrcode.make(config_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _generate_backup_codes(user) -> list[str]:
    StaticDevice.objects.filter(user=user, name=_BACKUP_DEVICE_NAME).delete()
    device = StaticDevice.objects.create(user=user, name=_BACKUP_DEVICE_NAME, confirmed=True)
    codes = []
    for _ in range(10):
        code = secrets.token_hex(4)
        StaticToken.objects.create(device=device, token=code)
        codes.append(code)
    return codes


def _settings_context(user, **extra) -> dict:
    from apps.accounts.models import DataExportRequest

    has_2fa = TOTPDevice.objects.filter(user=user, name=_DEVICE_NAME, confirmed=True).exists()
    pending_device = TOTPDevice.objects.filter(
        user=user, name=_DEVICE_NAME, confirmed=False
    ).first()
    ctx = {
        "has_2fa": has_2fa,
        "pending_device": pending_device,
        "export_requests": DataExportRequest.objects.filter(user=user)[:5],
    }
    if pending_device:
        ctx["qr_data_uri"] = _qr_data_uri(pending_device.config_url)
    ctx.update(extra)
    return ctx


class SettingsView(LoginRequiredMixin, View):
    login_url = "/login/"
    template_name = "dashboard/settings.html"

    def get(self, request):
        return render(request, self.template_name, _settings_context(request.user))


class PasswordChangeView(LoginRequiredMixin, View):
    login_url = "/login/"

    def post(self, request):
        current_password = request.POST.get("current_password", "")
        new_password1 = request.POST.get("new_password1", "")
        new_password2 = request.POST.get("new_password2", "")

        if not request.user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
            return redirect("settings")
        if new_password1 != new_password2:
            messages.error(request, "New passwords do not match.")
            return redirect("settings")
        try:
            validate_password(new_password1, user=request.user)
        except ValidationError as exc:
            for error in exc.messages:
                messages.error(request, error)
            return redirect("settings")

        request.user.set_password(new_password1)
        request.user.save(update_fields=["password"])
        update_session_auth_hash(request, request.user)
        messages.success(request, "Password updated.")
        return redirect("settings")


class TwoFactorSetupView(LoginRequiredMixin, View):
    login_url = "/login/"

    def post(self, request):
        if TOTPDevice.objects.filter(user=request.user, name=_DEVICE_NAME, confirmed=True).exists():
            messages.info(request, "Two-factor authentication is already enabled.")
            return redirect("settings")

        TOTPDevice.objects.filter(user=request.user, name=_DEVICE_NAME, confirmed=False).delete()
        TOTPDevice.objects.create(user=request.user, name=_DEVICE_NAME, confirmed=False)
        return redirect("settings")


class TwoFactorConfirmView(LoginRequiredMixin, View):
    login_url = "/login/"

    def post(self, request):
        device = TOTPDevice.objects.filter(
            user=request.user, name=_DEVICE_NAME, confirmed=False
        ).first()
        if not device:
            messages.error(request, "No two-factor setup in progress.")
            return redirect("settings")

        code = request.POST.get("code", "").strip().replace(" ", "")
        if not device.verify_token(code):
            messages.error(request, "Invalid code. Try again.")
            return redirect("settings")

        device.confirmed = True
        device.save()
        backup_codes = _generate_backup_codes(request.user)
        messages.success(request, "Two-factor authentication is now enabled.")
        return render(
            request,
            SettingsView.template_name,
            _settings_context(request.user, backup_codes=backup_codes),
        )


class TwoFactorDisableView(LoginRequiredMixin, View):
    login_url = "/login/"

    def post(self, request):
        password = request.POST.get("password", "")
        if not request.user.check_password(password):
            messages.error(request, "Incorrect password — 2FA was not disabled.")
            return redirect("settings")

        TOTPDevice.objects.filter(user=request.user, name=_DEVICE_NAME).delete()
        StaticDevice.objects.filter(user=request.user, name=_BACKUP_DEVICE_NAME).delete()
        messages.success(request, "Two-factor authentication disabled.")
        return redirect("settings")


class DataExportRequestView(LoginRequiredMixin, View):
    login_url = "/login/"

    def post(self, request):
        from apps.accounts.models import DataExportRequest
        from workers.tasks.data_export import generate_data_export_task

        if DataExportRequest.objects.filter(
            user=request.user,
            status__in=(DataExportRequest.STATUS_PENDING, DataExportRequest.STATUS_PROCESSING),
        ).exists():
            messages.info(request, "You already have an export in progress.")
            return redirect("settings")

        export_request = DataExportRequest.objects.create(user=request.user)
        generate_data_export_task.delay(export_request.pk)
        messages.success(request, "Your data export is being prepared — check back shortly.")
        return redirect("settings")


class DataExportDownloadView(LoginRequiredMixin, View):
    login_url = "/login/"

    def get(self, request, pk):
        from django.http import FileResponse, Http404

        from apps.accounts.models import DataExportRequest

        export_request = DataExportRequest.objects.filter(
            pk=pk, user=request.user, status=DataExportRequest.STATUS_READY,
        ).first()
        if export_request is None or not export_request.file:
            raise Http404

        return FileResponse(
            export_request.file.open("rb"),
            as_attachment=True,
            filename=f"webmail-data-export-{export_request.pk}.json",
        )


class AccountDeleteView(LoginRequiredMixin, View):
    login_url = "/login/"

    def post(self, request):
        from django.contrib.auth import logout

        from services.gdpr_service import anonymize_and_delete_account

        password = request.POST.get("password", "")
        confirm_text = request.POST.get("confirm_text", "").strip()

        if confirm_text != "DELETE":
            messages.error(request, 'Type "DELETE" to confirm — your account was not deleted.')
            return redirect("settings")
        if not request.user.check_password(password):
            messages.error(request, "Incorrect password — your account was not deleted.")
            return redirect("settings")

        anonymize_and_delete_account(request.user)
        logout(request)
        messages.success(request, "Your account and data have been deleted.")
        return redirect("login")

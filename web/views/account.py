from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.views import View
from django_otp import login as otp_login
from django_otp import match_token
from django_otp.plugins.otp_totp.models import TOTPDevice

from web.forms.auth_forms import LoginForm, SignUpForm


class SignUpView(View):
    template_name = "registration/signup.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("dashboard")
        return render(request, self.template_name, {"form": SignUpForm()})

    def post(self, request):
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            plan = request.GET.get("plan", "").strip()
            if plan and plan != "free":
                return redirect(f"/dashboard/billing/checkout/?plan={plan}")
            return redirect("dashboard")
        return render(request, self.template_name, {"form": form})


class LoginView(View):
    template_name = "registration/login.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("dashboard")
        return render(request, self.template_name, {"form": LoginForm()})

    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            if TOTPDevice.objects.filter(user=user, confirmed=True).exists():
                request.session["pre_2fa_user_id"] = user.pk
                request.session["pre_2fa_next"] = request.GET.get("next", "dashboard")
                return redirect("two_factor_verify")
            login(request, user)
            return redirect(request.GET.get("next", "dashboard"))
        return render(request, self.template_name, {"form": form})


class TwoFactorVerifyView(View):
    template_name = "registration/two_factor.html"

    def get(self, request):
        if not request.session.get("pre_2fa_user_id"):
            return redirect("login")
        return render(request, self.template_name, {})

    def post(self, request):
        user_id = request.session.get("pre_2fa_user_id")
        if not user_id:
            return redirect("login")

        from apps.accounts.models import CustomUser

        try:
            user = CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            request.session.pop("pre_2fa_user_id", None)
            return redirect("login")

        code = request.POST.get("code", "").strip().replace(" ", "")
        device = match_token(user, code) if code else None
        if device is None:
            return render(request, self.template_name, {"error": "Invalid code. Try again."})

        next_url = request.session.pop("pre_2fa_next", "dashboard")
        request.session.pop("pre_2fa_user_id", None)
        login(request, user)
        otp_login(request, device)
        return redirect(next_url)


class LogoutView(View):
    def post(self, request):
        logout(request)
        return redirect("home")

from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.views import View

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
            login(request, form.get_user())
            return redirect(request.GET.get("next", "dashboard"))
        return render(request, self.template_name, {"form": form})


class LogoutView(View):
    def post(self, request):
        logout(request)
        return redirect("home")

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.password_validation import validate_password

from apps.accounts.models import CustomUser


_INPUT_CSS = (
    "block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm "
    "shadow-sm placeholder-gray-400 focus:border-indigo-500 "
    "focus:outline-none focus:ring-1 focus:ring-indigo-500"
)


class SignUpForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "placeholder": "you@example.com",
            "autocomplete": "email",
            "class": _INPUT_CSS,
        })
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            "placeholder": "Min 8 characters",
            "autocomplete": "new-password",
            "class": _INPUT_CSS,
        }),
    )
    password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput(attrs={
            "placeholder": "Repeat password",
            "autocomplete": "new-password",
            "class": _INPUT_CSS,
        }),
    )

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_password1(self):
        password = self.cleaned_data.get("password1")
        validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords do not match.")
        return cleaned

    def save(self):
        email = self.cleaned_data["email"]
        password = self.cleaned_data["password1"]
        username = email.split("@")[0]
        base = username
        n = 1
        while CustomUser.objects.filter(username=username).exists():
            username = f"{base}{n}"
            n += 1
        return CustomUser.objects.create_user(username=username, email=email, password=password)


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "placeholder": "you@example.com",
            "autocomplete": "email",
            "class": _INPUT_CSS,
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "placeholder": "Password",
            "autocomplete": "current-password",
            "class": _INPUT_CSS,
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = None

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get("email", "").lower()
        password = cleaned.get("password")
        if email and password:
            try:
                user_obj = CustomUser.objects.get(email=email)
                username = user_obj.username
            except CustomUser.DoesNotExist as exc:
                raise forms.ValidationError("Invalid email or password.") from exc
            user = authenticate(username=username, password=password)
            if user is None:
                raise forms.ValidationError("Invalid email or password.")
            if not user.is_active:
                raise forms.ValidationError("This account is inactive.")
            self._user = user
        return cleaned

    def get_user(self):
        return self._user


class StyledSetPasswordForm(SetPasswordForm):
    """SetPasswordForm with Tailwind widget styling for the password reset confirm page."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ("new_password1", "new_password2"):
            self.fields[field].widget.attrs.update({"class": _INPUT_CSS})

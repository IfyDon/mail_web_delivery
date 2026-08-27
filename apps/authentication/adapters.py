"""allauth adapters wiring social login into our own account model/flows.

We don't use allauth's own login/signup pages or emails — our /login/ and
/signup/ views (web/views/account.py) stay the front door. These adapters
only govern the OAuth handshake: whether a brand-new social sign-in is
allowed to auto-create an account, and that the resulting CustomUser is
marked verified (Google/Microsoft already proved the email for us).
"""
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class AccountAdapter(DefaultAccountAdapter):
    """Disable allauth's own password-based signup — /signup/ is ours."""

    def is_open_for_signup(self, request):
        return False


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """Allow Google/Microsoft sign-in to create a new CustomUser, verified."""

    def is_open_for_signup(self, request, sociallogin):
        return True

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form=form)
        user.is_verified = True
        user.save(update_fields=['is_verified'])
        return user

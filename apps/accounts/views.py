"""
Account views for the VIPET accounts app.

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3, 4.4, 4.5, 13.7
"""

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin

from apps.accounts.models import CustomUser
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib import messages
from django.core.cache import cache
from django.core.mail import send_mail
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views import View
from django.views.generic.edit import FormView, UpdateView

from apps.accounts.forms import LoginForm, PasswordResetRequestForm, ProfileUpdateForm, RegistrationForm, SetNewPasswordForm

User = get_user_model()

# ---------------------------------------------------------------------------
# Rate-limiting constants (Requirement 2.5)
# ---------------------------------------------------------------------------
_RATE_LIMIT_FAILURES = 5       # max failed attempts
_RATE_LIMIT_WINDOW   = 900     # 15 minutes in seconds


class RegisterView(FormView):
    """
    Handles new user registration.

    - GET:  render the blank registration form.
    - POST: validate; if valid, create the user with a hashed password and
            redirect to the login page.
    - Authenticated users are redirected immediately to their role dashboard.
    """

    template_name = "accounts/register.html"
    form_class = RegistrationForm
    success_url = reverse_lazy("accounts:login")

    # ------------------------------------------------------------------
    # Pre-dispatch redirect for already-authenticated users (Req 13.7)
    # ------------------------------------------------------------------

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return _redirect_by_role(request.user)
        return super().dispatch(request, *args, **kwargs)

    # ------------------------------------------------------------------
    # Form handling
    # ------------------------------------------------------------------

    def form_valid(self, form):
        """Save the new user with a properly hashed password."""
        user = form.save(commit=False)
        user.set_password(form.cleaned_data["password"])
        user.save()
        return super().form_valid(form)


class LoginView(FormView):
    """
    Handles user authentication.

    - GET:  render the login form (redirect to dashboard if already authenticated).
    - POST: validate credentials, enforce rate limiting per IP, authenticate
            and redirect to role dashboard on success, show form error on failure.

    Rate limiting (Requirement 2.5):
        Key  = "login_fail:{ip}"
        Limit = 5 failures within 900 seconds (15 minutes).
        On exceed → non-field form error, no authentication attempt.
    """

    template_name = "accounts/login.html"
    form_class = LoginForm

    # ------------------------------------------------------------------
    # Pre-dispatch redirect for already-authenticated users (Req 13.7)
    # ------------------------------------------------------------------

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return _redirect_by_role(request.user)
        return super().dispatch(request, *args, **kwargs)

    # ------------------------------------------------------------------
    # Form handling
    # ------------------------------------------------------------------

    def form_valid(self, form):
        """Authenticate the user and redirect to the role dashboard."""
        request = self.request
        ip = _get_client_ip(request)
        cache_key = f"login_fail:{ip}"

        # Check rate limit before attempting authentication
        failures = cache.get(cache_key, 0)
        if failures >= _RATE_LIMIT_FAILURES:
            form.add_error(
                None,
                "Too many failed login attempts. Please try again in 15 minutes.",
            )
            return self.form_invalid(form)

        email = form.cleaned_data["email"]
        password = form.cleaned_data["password"]

        user = authenticate(request, username=email, password=password)

        if user is None:
            # Increment failure counter (set with timeout on first failure)
            cache.set(cache_key, failures + 1, timeout=_RATE_LIMIT_WINDOW)
            form.add_error(None, "Invalid email address or password.")
            return self.form_invalid(form)

        # Successful login — clear the failure counter
        cache.delete(cache_key)
        login(request, user)
        return _redirect_by_role(user)

    def form_invalid(self, form):
        """Render form with error messages."""
        return self.render_to_response(self.get_context_data(form=form))


class LogoutView(View):
    """
    Logs the user out and redirects to the public home page.

    Requirements: 2.4
    """

    def post(self, request, *args, **kwargs):
        logout(request)
        return redirect("/")

    # Also allow GET for convenience (e.g. simple link), though POST is preferred
    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect("/")


# ---------------------------------------------------------------------------
# Profile — Requirement 4
# ---------------------------------------------------------------------------

class ProfileView(LoginRequiredMixin, UpdateView):
    """
    Allows an authenticated user to view and update their profile.

    - GET:  render the profile form pre-populated with the user's current data.
            Email is displayed read-only in the template (not an editable field).
    - POST: validate and save changes; show a success message on redirect.
            If no profile photo has been uploaded, the template shows a default
            SVG avatar placeholder (Requirement 4.5).

    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
    """

    model = CustomUser
    form_class = ProfileUpdateForm
    template_name = "accounts/profile.html"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self, queryset=None):
        """Always edit the currently logged-in user (ignores URL pk/slug)."""
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Your profile has been updated successfully.")
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# Password Reset — Requirement 3
# ---------------------------------------------------------------------------

_token_generator = PasswordResetTokenGenerator()


class PasswordResetRequestView(FormView):
    """
    Step 1: User submits their email address to request a password reset link.

    - GET:  render the password reset request form.
    - POST: if email is registered, generate a token and send the reset email.
            Always show the same success message regardless of whether the
            email is registered (anti-enumeration, Requirement 3.1).
    """

    template_name = "accounts/password_reset.html"
    form_class = PasswordResetRequestForm

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            user = None

        if user is not None and user.is_active:
            uid   = urlsafe_base64_encode(force_bytes(user.pk))
            token = _token_generator.make_token(user)
            reset_url = self.request.build_absolute_uri(
                reverse_lazy(
                    "accounts:password_reset_confirm",
                    kwargs={"uidb64": uid, "token": token},
                )
            )
            send_mail(
                subject="VIPET — Password Reset Request",
                message=(
                    f"Hi {user.first_name},\n\n"
                    f"You requested a password reset for your VIPET account.\n\n"
                    f"Click the link below to choose a new password "
                    f"(valid for 60 minutes):\n\n{reset_url}\n\n"
                    f"If you did not request this, you can safely ignore this email.\n\n"
                    f"— The VIPET Team"
                ),
                from_email=None,          # uses DEFAULT_FROM_EMAIL from settings
                recipient_list=[user.email],
                fail_silently=True,       # never reveal whether email was sent
            )

        # Always render the same confirmation page (Requirement 3.1 — no enumeration)
        return self.render_to_response(
            self.get_context_data(form=form, email_sent=True)
        )


class PasswordResetConfirmView(FormView):
    """
    Step 2: User follows the reset link and sets a new password.

    - GET:  validate the uidb64/token; show the new-password form if valid,
            or an error page if the token is expired/invalid (Requirement 3.3).
    - POST: validate the token again, update the password, invalidate the
            token (it becomes invalid once the password hash changes, Req 3.4),
            and redirect to login (Requirement 3.2).
    """

    template_name  = "accounts/password_reset_confirm.html"
    form_class     = SetNewPasswordForm
    success_url    = reverse_lazy("accounts:login")

    # ------------------------------------------------------------------
    # Token validation helper
    # ------------------------------------------------------------------

    def _resolve_user_and_token(self, uidb64: str, token: str):
        """
        Return the user if uidb64 + token are valid, otherwise None.
        """
        try:
            uid  = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, OverflowError, TypeError):
            return None

        if not _token_generator.check_token(user, token):
            return None

        return user

    # ------------------------------------------------------------------
    # GET — show the form or an error
    # ------------------------------------------------------------------

    def get(self, request, uidb64: str, token: str, *args, **kwargs):
        user = self._resolve_user_and_token(uidb64, token)
        if user is None:
            # Expired or invalid token — show error with re-request link (Req 3.3)
            return self.render_to_response(
                self.get_context_data(token_valid=False)
            )
        return self.render_to_response(
            self.get_context_data(form=self.get_form(), token_valid=True)
        )

    # ------------------------------------------------------------------
    # POST — save the new password
    # ------------------------------------------------------------------

    def post(self, request, uidb64: str, token: str, *args, **kwargs):
        user = self._resolve_user_and_token(uidb64, token)
        if user is None:
            return self.render_to_response(
                self.get_context_data(token_valid=False)
            )

        form = self.get_form()
        if form.is_valid():
            user.set_password(form.cleaned_data["new_password"])
            user.save()
            # Token is now consumed — PasswordResetTokenGenerator hashes the
            # current password; after set_password() the old token will no
            # longer pass check_token() (Requirement 3.4).
            return redirect(self.success_url)

        return self.render_to_response(
            self.get_context_data(form=form, token_valid=True)
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _redirect_by_role(user):
    """Redirect an authenticated user to their role-appropriate dashboard."""
    if user.role == "admin":
        return redirect("/admin-panel/")
    return redirect("/client/")


def _get_client_ip(request) -> str:
    """Extract the real client IP, checking X-Forwarded-For first."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")

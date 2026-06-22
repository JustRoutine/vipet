"""
Account-related forms for the VIPET accounts app.

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.1, 2.2, 2.3, 3.1, 3.2, 4.1, 4.2, 4.3, 4.4, 4.5
"""

from django.core.exceptions import ValidationError
from django.forms import CharField, EmailField, EmailInput, Form, ModelForm, PasswordInput

from apps.accounts.models import CustomUser
from apps.core.validators import validate_image_file


class RegistrationForm(ModelForm):
    """
    Registration form for new client accounts.

    - password:  min 8, max 128 characters.
    - password2: confirmation field; must match password.
    - clean_email: rejects duplicate email addresses.
    - clean: validates password / password2 match.
    """

    password = CharField(
        widget=PasswordInput(attrs={"autocomplete": "new-password"}),
        min_length=8,
        max_length=128,
        label="Mot de passe",
    )
    password2 = CharField(
        widget=PasswordInput(attrs={"autocomplete": "new-password"}),
        label="Confirmer le mot de passe",
    )

    class Meta:
        model = CustomUser
        fields = ["first_name", "last_name", "email", "phone_number", "password"]

    # ------------------------------------------------------------------
    # Field-level validation
    # ------------------------------------------------------------------

    def clean_email(self) -> str:
        """Reject email addresses that are already registered."""
        email = self.cleaned_data["email"]
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError("Cette adresse e-mail est déjà enregistrée.")
        return email

    # ------------------------------------------------------------------
    # Cross-field validation
    # ------------------------------------------------------------------

    def clean(self) -> dict:
        """Validate that both password fields match."""
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("password2"):
            self.add_error("password2", "Les mots de passe ne correspondent pas.")
        return cleaned


class ProfileUpdateForm(ModelForm):
    """
    Form for authenticated users to update their profile.

    - Fields: first_name, last_name, phone_number, profile_photo.
    - email is excluded — it is displayed read-only in the template.
    - clean_profile_photo: validates MIME type and enforces a 5 MB size limit.

    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
    """

    class Meta:
        model = CustomUser
        fields = ["first_name", "last_name", "phone_number", "profile_photo"]

    def clean_profile_photo(self):
        """Validate the uploaded photo using the shared image validator (max 5 MB)."""
        photo = self.cleaned_data.get("profile_photo")
        if photo and hasattr(photo, "read"):
            # Only validate if a new file was uploaded (not an existing stored path).
            validate_image_file(photo, max_size_mb=5)
        return photo


class LoginForm(Form):
    """
    Login form accepting email and password.

    Used by LoginView (task 4.3).
    Requirements: 2.1, 2.2, 2.3
    """

    email = EmailField(
        label="Adresse e-mail",
        widget=EmailInput(attrs={"autocomplete": "email", "autofocus": True}),
    )
    password = CharField(
        label="Mot de passe",
        widget=PasswordInput(attrs={"autocomplete": "current-password"}),
    )


class PasswordResetRequestForm(Form):
    """
    Step 1 of password reset: accept an email address.

    Always shows the same success message whether the email is registered or
    not, preventing user enumeration (Requirement 3.1).
    """

    email = EmailField(
        label="Adresse e-mail",
        widget=EmailInput(attrs={"autocomplete": "email", "autofocus": True}),
    )


class SetNewPasswordForm(Form):
    """
    Step 2 of password reset: choose a new password (8–128 characters).

    Requirements: 3.2, 3.4
    """

    new_password = CharField(
        label="Nouveau mot de passe",
        min_length=8,
        max_length=128,
        widget=PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    new_password2 = CharField(
        label="Confirmer le nouveau mot de passe",
        widget=PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def clean(self) -> dict:
        """Validate that both password fields match."""
        cleaned = super().clean()
        p1 = cleaned.get("new_password")
        p2 = cleaned.get("new_password2")
        if p1 and p2 and p1 != p2:
            self.add_error("new_password2", "Les mots de passe ne correspondent pas.")
        return cleaned

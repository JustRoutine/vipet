"""
Contact form for the VIPET contact app.

Requirements: 17.1, 17.2, 17.6, 17.7, 17.8
"""

from django import forms

from apps.contact.models import ContactMessage


class ContactForm(forms.ModelForm):
    """
    ModelForm for submitting contact messages.

    Fields: name, email, subject, message.
    Excludes: is_read (always False on creation), created_at (auto).

    Validation:
      - name: required, max 100 characters
      - email: required, valid email format
      - subject: required, max 200 characters
      - message: required, max 2000 characters
    """

    class Meta:
        model = ContactMessage
        fields = ["name", "email", "subject", "message"]
        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Votre nom complet",
                "autocomplete": "name",
                "maxlength": "100",
            }),
            "email": forms.EmailInput(attrs={
                "placeholder": "vous@exemple.com",
                "autocomplete": "email",
                "maxlength": "254",
            }),
            "subject": forms.TextInput(attrs={
                "placeholder": "Objet de votre message",
                "maxlength": "200",
            }),
            "message": forms.Textarea(attrs={
                "placeholder": "Écrivez votre message ici...",
                "rows": 5,
                "maxlength": "2000",
            }),
        }
        error_messages = {
            "name": {
                "required": "Veuillez entrer votre nom.",
                "max_length": "Le nom ne doit pas dépasser 100 caractères.",
            },
            "email": {
                "required": "Veuillez entrer votre adresse e-mail.",
                "invalid": "Veuillez entrer une adresse e-mail valide.",
            },
            "subject": {
                "required": "Veuillez entrer un objet.",
                "max_length": "L'objet ne doit pas dépasser 200 caractères.",
            },
            "message": {
                "required": "Veuillez entrer un message.",
                "max_length": "Le message ne doit pas dépasser 2000 caractères.",
            },
        }

    def clean_name(self) -> str:
        """Validate name is non-empty and within length limit."""
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("Veuillez entrer votre nom.")
        if len(name) > 100:
            raise forms.ValidationError("Le nom ne doit pas dépasser 100 caractères.")
        return name

    def clean_subject(self) -> str:
        """Validate subject is non-empty and within length limit."""
        subject = self.cleaned_data.get("subject", "").strip()
        if not subject:
            raise forms.ValidationError("Veuillez entrer un objet.")
        if len(subject) > 200:
            raise forms.ValidationError("L'objet ne doit pas dépasser 200 caractères.")
        return subject

    def clean_message(self) -> str:
        """Validate message is non-empty and within length limit."""
        message = self.cleaned_data.get("message", "").strip()
        if not message:
            raise forms.ValidationError("Veuillez entrer un message.")
        if len(message) > 2000:
            raise forms.ValidationError("Le message ne doit pas dépasser 2000 caractères.")
        return message

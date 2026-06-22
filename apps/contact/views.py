"""
Contact views for the VIPET contact app.

Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7, 17.8
"""

from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView
from django.views.generic.edit import FormView

from apps.core.mixins import AdminRequiredMixin
from apps.contact.forms import ContactForm
from apps.contact.models import ContactMessage


class ContactPageView(FormView):
    """
    Public contact form page.

    - GET:  Render the empty contact form (accessible to all users).
    - POST: Validate the form; if valid, create a ContactMessage with
            is_read=False, show a success message, and redirect back to
            the contact page.

    Requirements: 17.1, 17.2, 17.6, 17.7, 17.8
    """

    template_name = "contact/contact.html"
    form_class = ContactForm
    success_url = reverse_lazy("contact:contact")

    def form_valid(self, form):
        """Save the contact message with is_read=False and show success."""
        contact_message = form.save(commit=False)
        contact_message.is_read = False
        contact_message.save()
        messages.success(
            self.request,
            "Votre message a été envoyé avec succès. Nous vous répondrons bientôt !",
        )
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# Admin views
# ---------------------------------------------------------------------------


class ContactAdminListView(AdminRequiredMixin, ListView):
    """
    Admin inbox: displays all contact messages ordered by newest first,
    with read/unread status visible.

    Requirement 17.3: Admin views all messages ordered by submission date
    descending with read/unread status indication.
    Requirement 17.5: Non-admin access is denied (403).
    """

    model = ContactMessage
    template_name = "contact/admin_list.html"
    context_object_name = "messages"
    ordering = ["-created_at"]


class ContactAdminDetailView(AdminRequiredMixin, DetailView):
    """
    Admin detail view: shows a single contact message and marks it as read
    on access.

    Requirement 17.4: Opening a contact message sets is_read to True.
    Requirement 17.5: Non-admin access is denied (403).
    """

    model = ContactMessage
    template_name = "contact/admin_detail.html"
    context_object_name = "message"

    def get_object(self, queryset=None):
        """Retrieve the message and mark it as read."""
        obj = super().get_object(queryset)
        if not obj.is_read:
            obj.is_read = True
            obj.save(update_fields=["is_read"])
        return obj

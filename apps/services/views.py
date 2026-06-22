"""
Service web views for the VIPET services app.

Provides a public service listing page with category filtering and admin
views for creating, updating, and deleting services.

Requirements: 8.1, 8.2, 8.3, 8.6, 8.7, 8.8, 8.9, 9.1, 9.2, 9.3, 9.4
"""

from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.core.mixins import AdminRequiredMixin
from apps.services.forms import ServiceForm
from apps.services.models import Service


class ServiceListView(ListView):
    """
    Public service listing page.

    Displays only services where is_available=True, ordered alphabetically
    by name. Supports optional category filtering via ?category= query param.

    No authentication required (public access).

    Requirements: 9.1, 9.2, 9.3, 9.4
    """

    model = Service
    template_name = "services/service_list.html"
    context_object_name = "services"

    def get_queryset(self):
        queryset = Service.objects.filter(is_available=True).order_by("name")

        # Filter by category if provided (Requirement 9.3)
        category = self.request.GET.get("category", "").strip()
        if category:
            queryset = queryset.filter(category=category)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Service.CATEGORY_CHOICES
        context["selected_category"] = self.request.GET.get("category", "")
        return context


class ServiceAdminCreateView(AdminRequiredMixin, CreateView):
    """
    Admin view to create a new service.

    Uses ServiceForm which validates all fields including image upload.
    Sets is_available to True by default (via model default).

    Requirements: 8.1, 8.6, 8.8
    """

    model = Service
    form_class = ServiceForm
    template_name = "services/service_form.html"
    success_url = reverse_lazy("services:service_list")

    def form_valid(self, form):
        messages.success(self.request, "Service créé avec succès.")
        return super().form_valid(form)


class ServiceAdminUpdateView(AdminRequiredMixin, UpdateView):
    """
    Admin view to update an existing service.

    Uses ServiceForm for validation. Allows toggling is_available field
    (Requirement 8.7).

    Requirements: 8.2, 8.6, 8.7, 8.8, 8.9
    """

    model = Service
    form_class = ServiceForm
    template_name = "services/service_form.html"
    success_url = reverse_lazy("services:service_list")

    def form_valid(self, form):
        messages.success(self.request, "Service mis à jour avec succès.")
        return super().form_valid(form)


class ServiceAdminDeleteView(AdminRequiredMixin, DeleteView):
    """
    Admin view to delete a service.

    Permanently removes the Service record from the system.

    Requirements: 8.3, 8.6, 8.9
    """

    model = Service
    template_name = "services/service_confirm_delete.html"
    success_url = reverse_lazy("services:service_list")

    def form_valid(self, form):
        # Remove the image file from storage before deleting the record
        if self.object.image:
            self.object.image.delete(save=False)
        messages.success(self.request, "Service supprimé avec succès.")
        return super().form_valid(form)

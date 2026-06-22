"""
Gallery web views for the VIPET gallery app.

Provides a public gallery page displaying published images and admin views
for uploading and deleting gallery images.

Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6, 16.7
"""

from django.core.exceptions import ValidationError
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView

from apps.core.mixins import AdminRequiredMixin
from apps.core.validators import validate_image_file
from apps.gallery.models import GalleryImage


class GalleryPublicView(ListView):
    """
    Public gallery page showing only published images.

    Displays GalleryImage records where is_published=True, ordered by
    uploaded_at descending (newest first). No authentication required.

    Requirements: 16.1
    """

    model = GalleryImage
    template_name = "gallery/gallery_public.html"
    context_object_name = "images"

    def get_queryset(self):
        return GalleryImage.objects.filter(is_published=True)


class GalleryAdminUploadView(AdminRequiredMixin, CreateView):
    """
    Admin view to upload a new gallery image.

    Validates:
    - Image file via validate_image_file (MIME type + size check)
    - Title: required, max 100 characters
    - Description: optional, max 500 characters

    Sets uploaded_by to the current admin user.

    Requirements: 16.2, 16.4, 16.5, 16.6, 16.7
    """

    model = GalleryImage
    fields = ["title", "description", "image", "is_published"]
    template_name = "gallery/gallery_upload.html"
    success_url = reverse_lazy("gallery:gallery_public")

    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user

        # Validate image file (MIME type and size)
        image_file = form.cleaned_data.get("image")
        if image_file:
            try:
                validate_image_file(image_file)
            except ValidationError as e:
                form.add_error("image", e)
                return self.form_invalid(form)

        # Validate title length (model enforces max_length=100, but explicit check)
        title = form.cleaned_data.get("title", "")
        if not title:
            form.add_error("title", "Ce champ est obligatoire.")
            return self.form_invalid(form)
        if len(title) > 100:
            form.add_error("title", "Le titre ne doit pas dépasser 100 caractères.")
            return self.form_invalid(form)

        # Validate description length
        description = form.cleaned_data.get("description", "")
        if len(description) > 500:
            form.add_error(
                "description", "La description ne doit pas dépasser 500 caractères."
            )
            return self.form_invalid(form)

        return super().form_valid(form)


class GalleryAdminDeleteView(AdminRequiredMixin, DeleteView):
    """
    Admin view to delete a gallery image.

    Removes both the GalleryImage record and the associated file from storage.

    Requirements: 16.3, 16.4
    """

    model = GalleryImage
    template_name = "gallery/gallery_confirm_delete.html"
    success_url = reverse_lazy("gallery:gallery_public")

    def form_valid(self, form):
        # Remove the image file from storage before deleting the record
        if self.object.image:
            self.object.image.delete(save=False)
        messages.success(self.request, "Image de la galerie supprimée avec succès.")
        return super().form_valid(form)

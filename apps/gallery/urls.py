"""
Gallery URL configuration.

Public URLs (included under /gallery/):
  /gallery/                → Public gallery page (GalleryPublicView)
  /gallery/upload/         → Admin image upload (GalleryAdminUploadView)
  /gallery/<int:pk>/delete/ → Admin image delete (GalleryAdminDeleteView)

Admin URLs (included under /admin-panel/gallery/):
  /admin-panel/gallery/upload/         → Admin image upload (GalleryAdminUploadView)
  /admin-panel/gallery/<int:pk>/delete/ → Admin image delete (GalleryAdminDeleteView)

Requirements: 16.1, 16.2, 16.3, 16.4
"""

from django.urls import path

from apps.gallery.views import (
    GalleryAdminDeleteView,
    GalleryAdminUploadView,
    GalleryPublicView,
)

app_name = "gallery"

# Public URL patterns (included at /gallery/)
urlpatterns = [
    path("", GalleryPublicView.as_view(), name="gallery_public"),
    path("upload/", GalleryAdminUploadView.as_view(), name="gallery_upload"),
    path("<int:pk>/delete/", GalleryAdminDeleteView.as_view(), name="gallery_delete"),
]

# Admin URL patterns (to be included at /admin-panel/gallery/)
admin_urlpatterns = [
    path("upload/", GalleryAdminUploadView.as_view(), name="admin_upload"),
    path("<int:pk>/delete/", GalleryAdminDeleteView.as_view(), name="admin_delete"),
]

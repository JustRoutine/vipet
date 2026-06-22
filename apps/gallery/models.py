"""
GalleryImage model for the VIPET gallery app.

Requirements: 16.1, 16.2
"""

from django.conf import settings
from django.db import models


class GalleryImage(models.Model):
    """
    A photo uploaded by an administrator for public display.

    - title: required, max 100 characters
    - description: optional, max 500 characters
    - image: uploaded to 'gallery/' directory
    - is_published: controls visibility on the public gallery page
    - uploaded_by: FK to AUTH_USER_MODEL with SET_NULL (preserves images if admin is deleted)
    - uploaded_at: auto-set on creation, used for ordering (newest first)
    """

    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=100)
    description = models.TextField(max_length=500, blank=True)
    image = models.ImageField(upload_to="gallery/")
    is_published = models.BooleanField(default=True, db_index=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self) -> str:
        return self.title

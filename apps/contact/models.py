"""
ContactMessage model for the VIPET contact app.

Requirements: 17.2, 17.6, 17.7
"""

from django.db import models


class ContactMessage(models.Model):
    """
    Stores public contact form submissions for admin review.

    Fields:
        name    — Submitter's name (max 100 chars, required)
        email   — Submitter's email address (max 254 chars, required)
        subject — Message subject (max 200 chars, required)
        message — Message body (max 2000 chars, required)
        is_read — Whether an admin has read the message (default False)
        created_at — Timestamp of submission
    """

    id         = models.BigAutoField(primary_key=True)
    name       = models.CharField(max_length=100)
    email      = models.EmailField(max_length=254)
    subject    = models.CharField(max_length=200)
    message    = models.TextField(max_length=2000)
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Contact Message"
        verbose_name_plural = "Contact Messages"

    def __str__(self) -> str:
        return f"{self.subject} — {self.name}"

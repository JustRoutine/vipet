"""
Reservation model for the VIPET reservations app.

Requirements: 10.4, 10.5, 11.1, 11.2, 11.3, 11.4, 11.6
"""

from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Reservation(models.Model):
    """
    Represents a booking linking a Pet to a Service with start/end dates
    and a status workflow enforced via allowed transitions.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    ALLOWED_TRANSITIONS = {
        "pending": ["approved", "rejected", "cancelled"],
        "approved": ["completed"],
        "rejected": [],
        "completed": [],
        "cancelled": [],
    }

    id = models.BigAutoField(primary_key=True)
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    pet = models.ForeignKey(
        "pets.Pet",
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    service = models.ForeignKey(
        "services.Service",
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    notes = models.TextField(max_length=500, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["client", "-created_at"],
                name="res_client_created_idx",
            ),
            models.Index(
                fields=["status", "-created_at"],
                name="res_status_created_idx",
            ),
        ]
        verbose_name = "Reservation"
        verbose_name_plural = "Reservations"

    def __str__(self) -> str:
        return (
            f"Reservation #{self.pk} - {self.pet} / {self.service} "
            f"({self.get_status_display()})"
        )

    def clean(self) -> None:
        """
        Model-level validation for reservation dates.

        - start_date must be >= today.
        - end_date must be > start_date.
        """
        super().clean()

        errors: dict[str, str] = {}

        if self.start_date is not None and self.start_date < date.today():
            errors["start_date"] = "La date de début doit être aujourd'hui ou dans le futur."

        if self.start_date is not None and self.end_date is not None:
            if self.end_date <= self.start_date:
                errors["end_date"] = "La date de fin doit être postérieure à la date de début."

        if errors:
            raise ValidationError(errors)

    def can_transition_to(self, new_status: str) -> bool:
        """Check if the transition from current status to new_status is allowed."""
        return new_status in self.ALLOWED_TRANSITIONS.get(self.status, [])

    def transition_to(self, new_status: str) -> None:
        """Perform the status transition if valid, else raise ValueError."""
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Impossible de passer de '{self.status}' à '{new_status}'. "
                f"Transitions autorisées : {self.ALLOWED_TRANSITIONS.get(self.status, [])}"
            )
        self.status = new_status
        self.save()

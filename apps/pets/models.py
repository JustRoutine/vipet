"""
Pet model for the VIPET pets app.

Requirements: 7.1, 7.7, 7.8, 7.9
"""

from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Pet(models.Model):
    """
    Represents a pet registered by a client.

    Each pet belongs to a single owner (client) and stores species, breed,
    gender, weight, medical notes, vaccination status, and an optional photo.
    """

    SPECIES_CHOICES = [
        ("dog", "Dog"),
        ("cat", "Cat"),
        ("bird", "Bird"),
        ("rabbit", "Rabbit"),
        ("other", "Other"),
    ]

    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("unknown", "Unknown"),
    ]

    VACCINATION_CHOICES = [
        ("up_to_date", "Up to Date"),
        ("overdue", "Overdue"),
        ("unknown", "Unknown"),
    ]

    id = models.BigAutoField(primary_key=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pets",
    )
    name = models.CharField(max_length=100)
    species = models.CharField(max_length=20, choices=SPECIES_CHOICES)
    breed = models.CharField(max_length=100, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    date_of_birth = models.DateField()
    weight = models.DecimalField(max_digits=5, decimal_places=2)  # 0.01–999.99 kg
    medical_notes = models.TextField(blank=True)
    vaccination_status = models.CharField(
        max_length=20, choices=VACCINATION_CHOICES, default="unknown"
    )
    photo = models.ImageField(upload_to="pets/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["owner", "-created_at"], name="pets_owner_created_idx"
            ),
        ]
        verbose_name = "Pet"
        verbose_name_plural = "Pets"

    def __str__(self) -> str:
        return f"{self.name} ({self.get_species_display()})"

    def clean(self) -> None:
        """
        Model-level validation for weight and date_of_birth.

        - Weight must be between 0.01 and 999.99 inclusive.
        - Date of birth must not be in the future.
        """
        super().clean()

        # Weight validation
        if self.weight is not None:
            if self.weight < Decimal("0.01"):
                raise ValidationError(
                    {"weight": "Le poids doit être d'au moins 0,01 kg."}
                )
            if self.weight > Decimal("999.99"):
                raise ValidationError(
                    {"weight": "Le poids ne doit pas dépasser 999,99 kg."}
                )

        # Date of birth validation
        if self.date_of_birth is not None and self.date_of_birth > date.today():
            raise ValidationError(
                {"date_of_birth": "La date de naissance ne peut pas être dans le futur."}
            )

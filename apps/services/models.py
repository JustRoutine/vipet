from django.db import models


class Service(models.Model):
    CATEGORY_CHOICES = [
        ("luxury_suite",       "Luxury Suite"),
        ("grooming",           "Grooming"),
        ("spa",                "Spa"),
        ("daycare",            "Daycare"),
        ("training",           "Training"),
        ("veterinary_checkup", "Veterinary Checkup"),
        ("birthday_events",    "Birthday Events"),
    ]

    id           = models.BigAutoField(primary_key=True)
    name         = models.CharField(max_length=100)
    category     = models.CharField(max_length=30, choices=CATEGORY_CHOICES, db_index=True)
    description  = models.TextField(max_length=1000)
    price        = models.DecimalField(max_digits=8, decimal_places=2)  # MAD, 0.01–9999.99
    is_available = models.BooleanField(default=True, db_index=True)
    image        = models.ImageField(upload_to="services/", null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Service"
        verbose_name_plural = "Services"

    def __str__(self) -> str:
        return f"{self.name} ({self.get_category_display()})"

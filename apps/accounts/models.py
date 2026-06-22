"""
CustomUser model and manager for the VIPET accounts app.

Requirements: 1.1, 2.1, 2.2
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class CustomUserManager(BaseUserManager):
    """
    Custom manager for CustomUser.

    - create_user: normalises email, sets is_active=True by default, hashes password.
    - create_superuser: additionally sets is_staff=True, is_superuser=True, role='admin'.
    """

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        if not email:
            raise ValueError("Une adresse e-mail est requise.")
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "admin")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Le superutilisateur doit avoir is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Le superutilisateur doit avoir is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model that uses email as the unique identifier instead of username.

    Roles:
        client — regular pet-owner user (default)
        admin  — platform administrator
    """

    ROLE_CHOICES = [
        ("client", "Client"),
        ("admin", "Admin"),
    ]

    id            = models.BigAutoField(primary_key=True)
    email         = models.EmailField(unique=True, max_length=254)
    first_name    = models.CharField(max_length=50)
    last_name     = models.CharField(max_length=50)
    phone_number  = models.CharField(max_length=20, blank=True)
    role          = models.CharField(max_length=10, choices=ROLE_CHOICES, default="client", db_index=True)
    profile_photo = models.ImageField(upload_to="profiles/", null=True, blank=True)
    is_active     = models.BooleanField(default=True)
    is_staff      = models.BooleanField(default=False)
    date_joined   = models.DateTimeField(auto_now_add=True, db_index=True)

    USERNAME_FIELD  = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = CustomUserManager()

    class Meta:
        verbose_name        = "User"
        verbose_name_plural = "Users"
        # email already has a unique index; role and date_joined carry db_index=True above.
        # Composite index useful for admin user-list queries filtered by role + join date.
        indexes = [
            models.Index(fields=["role", "date_joined"], name="accounts_user_role_joined_idx"),
        ]

    def __str__(self) -> str:
        return self.email

    def get_full_name(self) -> str:
        """Return the first and last name with a space in between."""
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self) -> str:
        """Return the first name."""
        return self.first_name

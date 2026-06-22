"""
Base Django settings for the VIPET project.
Shared across all environments (development, production).
"""

import os
from pathlib import Path

try:
    from decouple import config as decouple_config
except ImportError:
    def decouple_config(key, default=None, cast=None):  # type: ignore[misc]
        val = os.getenv(key, default)
        if cast is not None and val is not None:
            return cast(val)
        return val

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# BASE_DIR resolves to the repo root (parent of vipet/settings/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-csz9e9*=fgn@)yc%o(zgyj6vzlx48)1!y)_y4z38#t93dp(2_5",
)

DEBUG = False  # overridden per environment

ALLOWED_HOSTS: list[str] = []

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

_CLOUDINARY_CLOUD_NAME_CHECK = os.getenv("CLOUDINARY_CLOUD_NAME", "")
_CLOUDINARY_API_KEY_CHECK    = os.getenv("CLOUDINARY_API_KEY", "")
_CLOUDINARY_API_SECRET_CHECK = os.getenv("CLOUDINARY_API_SECRET", "")

THIRD_PARTY_APPS: list[str] = [
    "rest_framework",
    "rest_framework_simplejwt",
    "django_filters",
    *(
        ["cloudinary_storage", "cloudinary"]
        if _CLOUDINARY_CLOUD_NAME_CHECK and _CLOUDINARY_API_KEY_CHECK and _CLOUDINARY_API_SECRET_CHECK
        else []
    ),
]

LOCAL_APPS = [
    "apps.accounts.apps.AccountsConfig",
    "apps.pets.apps.PetsConfig",
    "apps.services.apps.ServicesConfig",
    "apps.reservations.apps.ReservationsConfig",
    "apps.notifications.apps.NotificationsConfig",
    "apps.gallery.apps.GalleryConfig",
    "apps.contact.apps.ContactConfig",
    "apps.dashboard.apps.DashboardConfig",
    "apps.core.apps.CoreConfig",
    "apps.promotions.apps.PromotionsConfig",
    "apps.cart.apps.CartConfig",
    "apps.orders.apps.OrdersConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "vipet.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "vipet.wsgi.application"

# ---------------------------------------------------------------------------
# Database — MySQL 8+, credentials from environment / .env
# Override ENGINE to sqlite3 in development.py for local use without MySQL.
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME":     decouple_config("DB_NAME",     default="vipet_db"),
        "USER":     decouple_config("DB_USER",     default="root"),
        "PASSWORD": decouple_config("DB_PASSWORD", default=""),
        "HOST":     decouple_config("DB_HOST",     default="127.0.0.1"),
        "PORT":     decouple_config("DB_PORT",     default="3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# ---------------------------------------------------------------------------
# Custom user model
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.CustomUser"  # set here so all apps see it

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

PASSWORD_RESET_TIMEOUT = 3600  # 60 minutes

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & media files
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------------------------------
# Cloudinary switchable backend (configured in task 1.2)
# ---------------------------------------------------------------------------
CLOUDINARY_CLOUD_NAME = _CLOUDINARY_CLOUD_NAME_CHECK
CLOUDINARY_API_KEY    = _CLOUDINARY_API_KEY_CHECK
CLOUDINARY_API_SECRET = _CLOUDINARY_API_SECRET_CHECK

if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    import cloudinary  # noqa: E402

    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
    )
    DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"
else:
    DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

# ---------------------------------------------------------------------------
# JWT settings (djangorestframework-simplejwt) — configured in task 1.2
# ---------------------------------------------------------------------------
from datetime import timedelta  # noqa: E402

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# ---------------------------------------------------------------------------
# Django REST Framework defaults
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
}

# ---------------------------------------------------------------------------
# Stripe
# ---------------------------------------------------------------------------
STRIPE_SECRET_KEY = decouple_config("STRIPE_SECRET_KEY", default="")
STRIPE_WEBHOOK_SECRET = decouple_config("STRIPE_WEBHOOK_SECRET", default="")

# ---------------------------------------------------------------------------
# Default primary key type
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

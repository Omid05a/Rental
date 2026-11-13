import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "insecure-dev-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost").split(",")

INSTALLED_APPS = [
    # Admin theme (must come before django.contrib.admin)
    "unfold",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "django.contrib.postgres",
    # Third-party
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    # Local apps
    "apps.users",
    "apps.vehicles",
    "apps.payments",
    "apps.bookings",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": os.environ["POSTGRES_DB"],
        "USER": os.environ["POSTGRES_USER"],
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
        "HOST": os.environ.get("DB_HOST", "db"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# The admin panel is in English (left-to-right) for now.
LANGUAGE_CODE = "en"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
PRIVATE_MEDIA_ROOT = BASE_DIR / "private_media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Rental API",
    "DESCRIPTION": "Peer-to-peer rental platform for cars and bicycles",
    "VERSION": "0.1.0",
    # Serve the Swagger UI files from this server instead of a public CDN.
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
}

from corsheaders.defaults import default_headers

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
]

# Allow the custom header used for idempotent payments and bookings.
CORS_ALLOW_HEADERS = (*default_headers, "idempotency-key")

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

# One-time password settings
OTP_EXPIRY_SECONDS = 120
OTP_RESEND_SECONDS = 60
OTP_MAX_ATTEMPTS = 5

# Booking rules
BOOKING_BUFFER_MINUTES = 30
BOOKING_MIN_HOURS = 1
BOOKING_MAX_DAYS = 14
BOOKING_MAX_ADVANCE_DAYS = 90
CANCEL_FREE_HOURS = 24
CANCEL_LATE_FEE_PERCENT = 50
COMMISSION_PERCENT = 15

# Admin theme settings
UNFOLD = {
    "SITE_TITLE": "Rental",
    "SITE_HEADER": "Rental",
    "SITE_SYMBOL": "key",
}

# Trip rules
TRIP_EARLY_START_MINUTES = 15
TRIP_RADIUS_TOLERANCE_M = 50
LATE_GRACE_MINUTES = 10
LATE_FEE_MULTIPLIER_PERCENT = 150
FUEL_TOLERANCE_PERCENT = 5
FUEL_FEE_PER_PERCENT = 20_000
FUEL_SERVICE_FEE = 100_000
MAX_DAMAGE_PHOTOS = 6
# Hours during which the owner may report damage (set a small value for demos).
DAMAGE_WINDOW_HOURS = float(os.environ.get("DAMAGE_WINDOW_HOURS", "24"))
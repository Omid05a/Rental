import os
import sys
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"

# Demo mode exposes the OTP code and the dev QR endpoint so the app can be
# shown without an SMS provider. Keep it off on any real server.
DEMO_MODE = os.environ.get("DJANGO_DEMO", "0") == "1"

# True when the site is served over HTTPS (set on the presentation host).
USE_HTTPS = os.environ.get("DJANGO_USE_HTTPS", "0") == "1"

TESTING = "test" in sys.argv

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG or TESTING:
        SECRET_KEY = "insecure-dev-key"
    else:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is not 1."
        )

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
    "apps.notifications",
    "apps.reviews",
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

# Rate limits for the login endpoints. Tests use very high limits so that
# repeated logins in the test suite are not blocked.
if TESTING:
    OTP_THROTTLE_RATES = {
        "otp_request_ip": "100000/hour",
        "otp_request_phone": "100000/hour",
        "otp_verify_ip": "100000/hour",
        "otp_verify_phone": "100000/hour",
    }
else:
    OTP_THROTTLE_RATES = {
        "otp_request_ip": "20/hour",
        "otp_request_phone": "5/hour",
        "otp_verify_ip": "60/hour",
        "otp_verify_phone": "20/hour",
    }

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_RATES": OTP_THROTTLE_RATES,
    # Set to the number of reverse proxies in front of the app, otherwise
    # every client appears to have the proxy's IP.
    "NUM_PROXIES": int(os.environ.get("DJANGO_NUM_PROXIES", "0")) or None,
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

# Comma-separated list, e.g. "http://localhost:3000,https://rental.example.com"
CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS", "http://localhost:3000"
).split(",")

# Needed for the admin panel when it is served over HTTPS.
CSRF_TRUSTED_ORIGINS = [
    origin
    for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin
]

# Allow the custom header used for idempotent payments and bookings.
CORS_ALLOW_HEADERS = (*default_headers, "idempotency-key")

# Transport security: only applied when the site really runs on HTTPS.
if USE_HTTPS:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False

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

# Reviews
REVIEW_WINDOW_DAYS = 14
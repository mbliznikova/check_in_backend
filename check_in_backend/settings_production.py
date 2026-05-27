"""
Production settings — overrides for check_in_backend.settings.

Usage:
    DJANGO_SETTINGS_MODULE=check_in_backend.settings_production

All base settings are inherited from settings.py. Only production-specific
values are defined here.
"""

import logging
import os
from pathlib import Path

import sentry_sdk
from dotenv import load_dotenv

from check_in_backend.settings import *  # noqa: F401, F403

load_dotenv()

# ── Security ──────────────────────────────────────────────────────────────────

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

DEBUG = False

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
    if h.strip()
]

# ── CORS ──────────────────────────────────────────────────────────────────────

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
    if o.strip()
]

# ── Database (PostgreSQL) ─────────────────────────────────────────────────────

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["DB_NAME"],
        "USER": os.environ["DB_USER"],
        "PASSWORD": os.environ["DB_PASSWORD"],
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

# ── Static files ──────────────────────────────────────────────────────────────
# collectstatic dumps files to staticfiles/; serve that directory via your
# platform's static hosting or a CDN. Django admin CSS/JS needs this.

BASE_DIR = Path(__file__).resolve().parent.parent

STATIC_ROOT = BASE_DIR / "staticfiles"

# ── Celery ────────────────────────────────────────────────────────────────────

CELERY_BROKER_URL = os.environ["REDIS_URL"]
CELERY_RESULT_BACKEND = os.environ["REDIS_URL"]

# ── HTTPS / security headers ──────────────────────────────────────────────────
# SECURE_SSL_REDIRECT:
#   False  — managed platforms (Railway, Render, Heroku): platform terminates SSL
#   True   — VPS with Nginx: Django can enforce the redirect itself

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "False") == "True"
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# ── Error tracking (Sentry) ───────────────────────────────────────────────────

_sentry_dsn = os.environ.get("SENTRY_DSN")
if _sentry_dsn:
    sentry_sdk.init(dsn=_sentry_dsn, traces_sample_rate=0.1)
else:
    logging.warning("SENTRY_DSN is not set; error tracking is disabled.")

# ── Logging ───────────────────────────────────────────────────────────────────
# Capture WARNING+ to file; keep console for platform log aggregators.

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "WARNING",
            "class": "logging.FileHandler",
            "filename": "django_errors.log",
        },
        "console": {
            "level": "WARNING",
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "WARNING",
            "propagate": True,
        },
        "backend": {
            "handlers": ["console", "file"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

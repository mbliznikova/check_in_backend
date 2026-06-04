"""
CI/test settings — overrides for check_in_backend.settings_production.

Usage:
    DJANGO_SETTINGS_MODULE=check_in_backend.settings_test

Required environment variables (same as production, but REDIS_URL does not
need to point to a real instance — it satisfies the _REQUIRED check and is
then overridden by the locmem cache below):
    DJANGO_SECRET_KEY, DB_NAME, DB_USER, DB_PASSWORD, REDIS_URL
"""

from check_in_backend.settings_production import *  # noqa: F401, F403

# Use in-process cache — no Redis service needed in CI.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Run Celery tasks synchronously in the test process — no broker needed.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# MD5 is much faster than the default PBKDF2 for tests.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

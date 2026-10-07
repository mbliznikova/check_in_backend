import logging
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

CLERK_DELETE_MAX_ATTEMPTS = 3
CLERK_DELETE_BACKOFF_SECONDS = 1.0


class ClerkDeleteError(Exception):
    """Raised when Clerk's Backend API user-delete call fails after every
    retry. The caller's local DB row is already deleted by this point —
    get-only auth means a lingering Clerk identity can never again resolve
    to a local User, so this is a manual-cleanup concern, not a data-
    integrity one."""


def delete_clerk_user(clerk_user_id):
    """Deletes a user via Clerk's Backend API, with a bounded retry for
    transient failures. A 404 (already gone) counts as success."""
    if not clerk_user_id:
        return

    url = f"https://api.clerk.com/v1/users/{clerk_user_id}"
    headers = {"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"}

    last_error = None
    for attempt in range(1, CLERK_DELETE_MAX_ATTEMPTS + 1):
        try:
            response = requests.delete(url, headers=headers, timeout=10)
            if response.status_code in (200, 202, 204, 404):
                return
            last_error = f"Clerk API returned {response.status_code}: {response.text}"
        except requests.RequestException as e:
            last_error = f"Clerk API request failed: {e}"

        if attempt < CLERK_DELETE_MAX_ATTEMPTS:
            time.sleep(CLERK_DELETE_BACKOFF_SECONDS * attempt)

    raise ClerkDeleteError(last_error)

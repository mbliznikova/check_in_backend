import logging
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

CLERK_API_BASE_URL = "https://api.clerk.com/v1"
CLERK_DELETE_MAX_ATTEMPTS = 3
CLERK_DELETE_BACKOFF_SECONDS = 1.0


class ClerkDeleteError(Exception):
    """Raised when Clerk's Backend API user-delete call fails after every
    retry. The caller's local DB row is already deleted by this point —
    get-only auth means a lingering Clerk identity can never again resolve
    to a local User, so this is a manual-cleanup concern, not a data-
    integrity one."""


class ClerkOrgDeleteError(Exception):
    """Raised when Clerk's Backend API organization-delete call fails after
    every retry. Non-fatal to the caller by design — an orphaned Org has no
    login/auth surface, so this is a manual-cleanup concern, not a request
    failure (see delete_account's handling)."""


def _delete_clerk_resource(url):
    """Shared bounded-retry DELETE against a Clerk Backend API resource URL.
    Returns normally on success (incl. 404 = already gone); raises
    RuntimeError with the last error after exhausting retries, for the
    caller to wrap in a resource-specific exception type."""
    headers = {"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"}

    last_error = None
    for attempt in range(1, CLERK_DELETE_MAX_ATTEMPTS + 1):
        try:
            response = requests.delete(url, headers=headers, timeout=10)
            if response.status_code in (200, 202, 204, 404):
                logger.info(
                    "Clerk DELETE succeeded url=%s status=%s attempt=%d/%d",
                    url, response.status_code, attempt, CLERK_DELETE_MAX_ATTEMPTS,
                )
                return
            last_error = f"Clerk API returned {response.status_code}: {response.text}"
        except requests.RequestException as e:
            last_error = f"Clerk API request failed: {e}"

        logger.warning(
            "Clerk DELETE attempt %d/%d failed url=%s: %s",
            attempt, CLERK_DELETE_MAX_ATTEMPTS, url, last_error,
        )

        if attempt < CLERK_DELETE_MAX_ATTEMPTS:
            time.sleep(CLERK_DELETE_BACKOFF_SECONDS * attempt)

    logger.error(
        "Clerk DELETE exhausted all %d attempts url=%s: %s",
        CLERK_DELETE_MAX_ATTEMPTS, url, last_error,
    )
    raise RuntimeError(last_error)


def delete_clerk_user(clerk_user_id):
    """Deletes a user via Clerk's Backend API, with a bounded retry for
    transient failures. A 404 (already gone) counts as success."""
    if not clerk_user_id:
        return

    try:
        _delete_clerk_resource(f"{CLERK_API_BASE_URL}/users/{clerk_user_id}")
    except RuntimeError as e:
        raise ClerkDeleteError(str(e))


def delete_clerk_organization(clerk_org_id):
    """Deletes an organization via Clerk's Backend API, with a bounded retry
    for transient failures. A 404 (already gone) counts as success."""
    if not clerk_org_id:
        return

    try:
        _delete_clerk_resource(f"{CLERK_API_BASE_URL}/organizations/{clerk_org_id}")
    except RuntimeError as e:
        raise ClerkOrgDeleteError(str(e))

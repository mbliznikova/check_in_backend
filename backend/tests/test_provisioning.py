"""HTTP-level tests for the auth/provisioning split: read-only middleware
authentication plus the explicit POST /backend/me/provision/ endpoint."""
import json
from unittest.mock import patch

from django.test import TestCase

from backend.models import User


class ProvisioningEndpointTests(TestCase):

    def _mock_clerk_token(self, payload):
        return patch(
            "backend.middleware.verify_token.verify_clerk_token",
            return_value=payload,
        )

    def test_existing_user_authenticates_with_no_new_write(self):
        User.objects.create(
            clerk_user_id="user_existing",
            email="existing@example.com",
            username="user_existing",
        )
        payload = {
            "sub": "user_existing",
            "email": "existing@example.com",
            "email_verified": True,
        }

        with self._mock_clerk_token(payload):
            response = self.client.get(
                "/backend/me/", HTTP_AUTHORIZATION="Bearer test-token")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)

    def test_new_user_provisions_via_endpoint(self):
        payload = {
            "sub": "user_new",
            "email": "new@example.com",
            "email_verified": False,
            "first_name": "New",
            "last_name": "User",
        }

        with self._mock_clerk_token(payload):
            response = self.client.post(
                "/backend/me/provision/", HTTP_AUTHORIZATION="Bearer test-token")

        self.assertEqual(response.status_code, 200)
        user = User.objects.get(clerk_user_id="user_new")
        self.assertEqual(user.username, "user_new")
        self.assertEqual(user.email, "new@example.com")

        response_data = json.loads(response.content)
        self.assertEqual(response_data["userId"], user.id)
        self.assertEqual(response_data["memberships"], [])

    def test_delete_recreate_same_verified_email_links_cleanly(self):
        old_user = User.objects.create(
            clerk_user_id="user_old",
            email="shared@example.com",
            username="user_old",
        )
        payload = {
            "sub": "user_new",
            "email": "shared@example.com",
            "email_verified": True,
        }

        with self._mock_clerk_token(payload):
            response = self.client.post(
                "/backend/me/provision/", HTTP_AUTHORIZATION="Bearer test-token")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)
        old_user.refresh_from_db()
        self.assertEqual(old_user.clerk_user_id, "user_new")

    def test_unknown_token_on_normal_endpoint_creates_nothing(self):
        payload = {
            "sub": "user_unknown",
            "email": "unknown@example.com",
            "email_verified": True,
        }

        with self._mock_clerk_token(payload):
            response = self.client.get(
                "/backend/me/", HTTP_AUTHORIZATION="Bearer test-token")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(User.objects.count(), 0)

    def test_unverified_email_collision_returns_conflict_not_401(self):
        User.objects.create(
            clerk_user_id="user_old",
            email="shared@example.com",
            username="user_old",
        )
        payload = {
            "sub": "user_new",
            "email": "shared@example.com",
            "email_verified": False,
        }

        with self._mock_clerk_token(payload):
            response = self.client.post(
                "/backend/me/provision/", HTTP_AUTHORIZATION="Bearer test-token")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(
            User.objects.get(email="shared@example.com").clerk_user_id, "user_old")

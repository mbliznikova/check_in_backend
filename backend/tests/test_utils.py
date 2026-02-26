"""Shared test utilities and base classes for integration tests."""
import json
from unittest.mock import patch

from django.test import TestCase

from backend.models import School, SchoolMembership, User
from backend.services.user_sync import sync_clerk_user

FAKE_CLERK_PAYLOAD = {
    "sub": "clerk_test_user_123",
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User",
}


class BaseTestCase(TestCase):
    """Base class for all integration tests - handles auth mocking and common setup."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.verify_patch = patch(
            "backend.middleware.verify_token.verify_clerk_token",
            return_value=FAKE_CLERK_PAYLOAD,
        )
        cls.verify_patch.start()

    @classmethod
    def tearDownClass(cls):
        cls.verify_patch.stop()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.client.defaults["HTTP_AUTHORIZATION"] = "Bearer test-token"

        sync_clerk_user(
            clerk_user_id=FAKE_CLERK_PAYLOAD["sub"],
            user_email=FAKE_CLERK_PAYLOAD["email"],
            extra_fields={
                "first_name": FAKE_CLERK_PAYLOAD["first_name"],
                "last_name": FAKE_CLERK_PAYLOAD["last_name"],
            },
        )

        self.school = School.objects.create(
            name="Test School", clerk_org_id="test_org_123"
        )
        user = User.objects.get(clerk_user_id=FAKE_CLERK_PAYLOAD["sub"])
        self.membership = SchoolMembership.objects.create(
            user=user, school=self.school, role="owner"
        )
        self.client.defaults["HTTP_X_SCHOOL_ID"] = self.school.id

    def positive_response_helper(self, response, expected_status, message):
        """Assert response has expected status code and success message."""
        self.assertEqual(response.status_code, expected_status)
        response_data = json.loads(response.content)
        self.assertIn("message", response_data)
        self.assertEqual(response_data.get("message"), message)

    def error_response_helper(self, response, expected_code, expected_message):
        """Assert response has expected error status code and error message."""
        self.assertEqual(response.status_code, expected_code)
        response_data = json.loads(response.content)
        self.assertIn("error", response_data)
        self.assertEqual(response_data.get("error"), expected_message)

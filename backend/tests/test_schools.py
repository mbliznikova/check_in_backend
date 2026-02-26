"""Tests for school management functionality."""
import json

from django.contrib.auth import get_user_model
from django.urls import reverse

from ..models import School, SchoolMembership
from .test_utils import FAKE_CLERK_PAYLOAD, BaseTestCase

User = get_user_model()


class SchoolsTestCase(BaseTestCase):
    """Tests for school management endpoints."""

    def positive_response_helper(self, response, expected_status, message):
        """Assert response has expected status and success message."""
        self.assertEqual(response.status_code, expected_status)
        response_data = json.loads(response.content)
        self.assertIn("message", response_data)
        self.assertEqual(response_data.get("message"), message)

    def error_response_helper(self, response, expected_code, expected_message):
        """Assert response has expected error status and message."""
        self.assertEqual(response.status_code, expected_code)
        response_data = json.loads(response.content)
        self.assertIn("error", response_data)
        self.assertEqual(response_data.get("error"), expected_message)

    def setUp(self):
        super().setUp()
        self.schools_url = reverse("schools")
        self.school_detail_url = reverse(
            "school_detail", args=[self.school.id])
        self.edit_school_url = reverse("edit_school", args=[self.school.id])
        self.delete_school_url = reverse(
            "delete_school", args=[self.school.id])

    def test_get_schools_list_successfully(self):
        response = self.client.get(self.schools_url)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn("response", response_data)
        self.assertEqual(len(response_data["response"]), 1)
        self.assertEqual(response_data["response"][0]["id"], self.school.id)
        self.assertEqual(
            response_data["response"][0]["name"],
            self.school.name)

    def test_get_schools_empty_list(self):
        # Delete the membership created in setUp to simulate a user with no
        # school memberships
        self.membership.delete()
        response = self.client.get(self.schools_url)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn("response", response_data)
        self.assertEqual(len(response_data["response"]), 0)

    def test_create_school_successfully(self):
        request_data = {
            "name": "New School",
            "clerkOrgId": "new_org_456",
            "phone": "+1234567890",
            "address": "123 Main St",
            "logoUrl": "https://example.com/logo.png",
        }
        response = self.client.post(
            self.schools_url,
            json.dumps(request_data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        response_data = json.loads(response.content)
        self.assertIn("message", response_data)
        self.assertEqual(
            response_data["message"],
            "School created successfully")
        self.assertEqual(response_data["name"], "New School")
        self.assertEqual(response_data["clerkOrgId"], "new_org_456")

        # Verify the user was set as owner
        new_school = School.objects.get(id=response_data["id"])
        membership = SchoolMembership.objects.get(
            user=User.objects.get(clerk_user_id=FAKE_CLERK_PAYLOAD["sub"]),
            school=new_school,
        )
        self.assertEqual(membership.role, "owner")

    def test_create_school_duplicate_clerk_org_id(self):
        # Try to create a school with the same clerk_org_id as self.school
        request_data = {
            "name": "Duplicate Org School",
            "clerkOrgId": self.school.clerk_org_id,
        }
        response = self.client.post(
            self.schools_url,
            json.dumps(request_data),
            content_type="application/json",
        )
        self.error_response_helper(
            response, 400, "School with this clerk organization ID already exists")

    def test_create_school_missing_required_fields(self):
        request_data = {"name": "Incomplete School"}
        response = self.client.post(
            self.schools_url,
            json.dumps(request_data),
            content_type="application/json",
        )
        self.error_response_helper(
            response, 400, "Name and clerkOrgId are required")

    def test_get_school_detail_successfully(self):
        response = self.client.get(self.school_detail_url)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn("response", response_data)
        self.assertEqual(response_data["response"]["id"], self.school.id)
        self.assertEqual(response_data["response"]["name"], self.school.name)

    def test_get_school_detail_school_not_found(self):
        non_existent_id = 9999
        detail_url = reverse("school_detail", args=[non_existent_id])
        response = self.client.get(detail_url)
        self.error_response_helper(response, 404, "School not found")

    def test_edit_school_successfully(self):
        request_data = {"name": "Updated School Name", "phone": "+1234567890"}
        response = self.client.patch(
            self.edit_school_url,
            json.dumps(request_data),
            content_type="application/json",
        )
        self.positive_response_helper(
            response, 200, "School was updated successfully")
        response_data = json.loads(response.content)
        self.assertEqual(response_data["name"], "Updated School Name")
        self.assertEqual(response_data["phone"], "+1234567890")

    def test_edit_school_empty_name_validation(self):
        request_data = {"name": ""}
        response = self.client.patch(
            self.edit_school_url,
            json.dumps(request_data),
            content_type="application/json",
        )
        self.error_response_helper(
            response, 400, "School name cannot be empty")

    def test_delete_school_successfully(self):
        response = self.client.delete(self.delete_school_url)
        self.positive_response_helper(
            response, 200, f"School {
                self.school.name} was deleted successfully")
        self.assertFalse(School.objects.filter(id=self.school.id).exists())

    def test_delete_school_not_found(self):
        non_existent_id = 9999
        delete_url = reverse("delete_school", args=[non_existent_id])
        response = self.client.delete(delete_url)
        self.error_response_helper(response, 404, "School not found")

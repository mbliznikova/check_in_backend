"""Tests for student functionality."""
import json

from django.urls import reverse

from .test_utils import BaseTestCase


class StudentsTestCase(BaseTestCase):
    """Tests for the students endpoint (POST /students/)."""

    def positive_response_content_helper(
        self, response, expected_first_name, expected_last_name
    ):
        """Assert response contains student ID and names."""
        response_data = json.loads(response.content)
        self.assertIn("studentId", response_data)
        self.assertIn("firstName", response_data)
        self.assertIn("lastName", response_data)
        self.assertEqual(response_data["firstName"], expected_first_name)
        self.assertEqual(response_data["lastName"], expected_last_name)

    def error_response_helper(self, response, expected_code, expected_message):
        """Assert error response."""
        self.assertEqual(response.status_code, expected_code)
        response_data = json.loads(response.content)
        self.assertIn("error", response_data)
        self.assertEqual(response_data.get("error"), expected_message)

    def setUp(self):
        super().setUp()
        self.students_url = reverse("students")
        self.first_name_one = "First"
        self.last_name_one = "Last"

    def test_create_student_successfully(self):
        request_data = {
            "firstName": self.first_name_one,
            "lastName": self.last_name_one,
            "school": self.school.id,
        }

        response = self.client.post(
            self.students_url,
            json.dumps(request_data),
            content_type="application/json",
        )
        self.positive_response_helper(
            response, 200, "Student was created successfully")
        self.positive_response_content_helper(
            response=response,
            expected_first_name=self.first_name_one,
            expected_last_name=self.last_name_one,
        )

    def test_student_with_empty_both_first_last_names_not_created(self):
        request_data = {
            "firstName": "",
            "lastName": "",
            "school": self.school.id,
        }

        response = self.client.post(
            self.students_url,
            json.dumps(request_data),
            content_type="application/json",
        )
        self.error_response_helper(
            response, 400, "First and last name should not be empty"
        )

    def test_student_with_empty_first_name_not_created(self):
        request_data = {
            "firstName": "",
            "lastName": self.last_name_one,
            "school": self.school.id,
        }

        response = self.client.post(
            self.students_url,
            json.dumps(request_data),
            content_type="application/json",
        )
        self.error_response_helper(
            response, 400, "First and last name should not be empty"
        )


# TODO: Add tests for updating and deleting students (PUT/PATCH
# /students/<id>/ and DELETE)

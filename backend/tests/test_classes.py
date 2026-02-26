"""Tests for class and class occurrence functionality."""
import json
from datetime import time

from django.db import IntegrityError, transaction
from django.urls import reverse

from ..models import ClassModel, Day, Schedule
from .test_utils import BaseTestCase


class ClassesTestCase(BaseTestCase):
    """Tests for the classes endpoint (POST /classes/)."""

    def positive_response_content_helper(
        self, response, expected_class_name=""
    ):
        """Assert response contains class ID and name."""
        response_data = json.loads(response.content)
        self.assertIn("id", response_data)
        self.assertIn("name", response_data)
        if expected_class_name:
            self.assertEqual(response_data["name"], expected_class_name)

    def error_response_helper(self, response, expected_code, expected_message):
        """Assert error response."""
        self.assertEqual(response.status_code, expected_code)
        response_data = json.loads(response.content)
        self.assertIn("error", response_data)
        self.assertEqual(response_data.get("error"), expected_message)

    def setUp(self):
        super().setUp()
        self.classes_url = reverse("classes")
        self.class_one_name = "Test Class One"

    def test_create_class_successfully(self):
        request_data = {"name": self.class_one_name, "school": self.school.id}

        response = self.client.post(
            self.classes_url,
            json.dumps(request_data),
            content_type="application/json",
        )
        self.positive_response_helper(
            response, 200, "Class was created successfully")
        self.positive_response_content_helper(
            response=response, expected_class_name=self.class_one_name
        )

    def test_class_with_empty_name_not_created(self):
        request_data = {"name": "", "school": self.school.id}

        response = self.client.post(
            self.classes_url,
            json.dumps(request_data),
            content_type="application/json",
        )
        self.error_response_helper(
            response, 400, "Class name should not be empty")


class SchedulesTestCase(BaseTestCase):
    """Tests for the schedules endpoint (POST /schedules/)."""

    def positive_response_content_helper(
        self,
        response,
        expected_class_id,
        expected_class_name,
        expected_day,
        expected_time,
    ):
        """Assert response contains schedule details."""
        response_data = json.loads(response.content)
        self.assertIn("classId", response_data)
        self.assertIn("className", response_data)
        self.assertIn("day", response_data)
        self.assertIn("time", response_data)

        self.assertEqual(response_data.get("classId"), expected_class_id)
        self.assertEqual(response_data.get("className"), expected_class_name)
        self.assertEqual(response_data.get("day"), expected_day)
        self.assertEqual(response_data.get("time"), expected_time)

    def error_response_helper(self, response, expected_code, expected_message):
        """Assert error response."""
        self.assertEqual(response.status_code, expected_code)
        response_data = json.loads(response.content)
        self.assertIn("error", response_data)
        self.assertEqual(response_data.get("error"), expected_message)

    def setUp(self):
        super().setUp()
        self.schedules_url = reverse("schedules")
        self.class_one = ClassModel.objects.create(
            name="Foil", school=self.school)
        self.class_two = ClassModel.objects.create(
            name="Heavy sabre", school=self.school)
        self.day_one = Day.objects.create(name="Monday")
        self.day_two = Day.objects.create(name="Tuesday")
        self.time_one = "10:00:00"
        self.time_two = "15:00:00"

    def test_schedule_class_successfully(self):
        request_data = {
            "classId": self.class_one.id,
            "day": self.day_one.name,
            "classTime": self.time_one,
            "school": self.school.id,
        }

        response = self.client.post(
            self.schedules_url,
            json.dumps(request_data),
            content_type="application/json",
        )
        self.positive_response_helper(
            response, 200, "Schedule was created successfully")
        self.positive_response_content_helper(
            response=response,
            expected_class_id=self.class_one.id,
            expected_class_name=self.class_one.name,
            expected_day=self.day_one.name,
            expected_time=self.time_one,
        )

    def test_class_with_incorrect_fields_not_scheduled(self):
        request_data = {
            "classId": None,
            "day": None,
            "classTime": self.time_one,
            "school": self.school.id,
        }

        response = self.client.post(
            self.schedules_url,
            json.dumps(request_data),
            content_type="application/json",
        )
        self.error_response_helper(response, 400, "Missing required fields")

    def test_class_with_incorrect_class_id_not_scheduled(self):
        request_data = {
            "classId": 12354,
            "day": self.day_one.name,
            "classTime": self.time_one,
            "school": self.school.id,
        }

        response = self.client.post(
            self.schedules_url,
            json.dumps(request_data),
            content_type="application/json",
        )
        self.error_response_helper(response, 404, "Class not found")

    def test_class_with_incorrect_day_name_not_scheduled(self):
        request_data = {
            "classId": self.class_one.id,
            "day": "Mon",
            "classTime": self.time_one,
            "school": self.school.id,
        }

        response = self.client.post(
            self.schedules_url,
            json.dumps(request_data),
            content_type="application/json",
        )
        self.error_response_helper(response, 404, "Day not found")

    def test_class_with_incorrect_time_format_not_scheduled(self):
        request_data = {
            "classId": self.class_one.id,
            "day": self.day_one.name,
            "classTime": "3PM",
            "school": self.school.id,
        }

        response = self.client.post(
            self.schedules_url,
            json.dumps(request_data),
            content_type="application/json",
        )
        self.error_response_helper(response, 400, "Invalid time format")

    def test_can_not_schedule_two_classes_at_the_same_day_and_time(self):
        request_data_one = {
            "classId": self.class_one.id,
            "day": self.day_one.name,
            "classTime": self.time_one,
            "school": self.school.id,
        }

        request_data_two = {
            "classId": self.class_two.id,
            "day": self.day_one.name,
            "classTime": self.time_one,
            "school": self.school.id,
        }

        response = self.client.post(
            self.schedules_url,
            json.dumps(request_data_one),
            content_type="application/json",
        )
        self.positive_response_helper(
            response, 200, "Schedule was created successfully")
        self.positive_response_content_helper(
            response=response,
            expected_class_id=self.class_one.id,
            expected_class_name=self.class_one.name,
            expected_day=self.day_one.name,
            expected_time=self.time_one,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Schedule.objects.create(
                    class_model=self.class_two,
                    day=self.day_one,
                    class_time=time(10, 0, 0),
                    school=self.school,
                )

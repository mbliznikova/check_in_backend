"""Tests for available time slots calculation."""
import json
from datetime import time

from django.test import TestCase
from django.urls import reverse
from django.utils.dateparse import parse_time
from django.utils.timezone import now

from ..models import ClassModel, Day, Schedule
from .test_utils import BaseTestCase


class TimeSlotsTestCase(BaseTestCase):
    """Tests for the available_time_slots endpoint (GET /available_time_slots/)."""

    def positive_response_helper(self, response, expected_status, message):
        """Assert response has expected status and message."""
        self.assertEqual(response.status_code, expected_status)
        response_data = json.loads(response.content)
        self.assertIn("message", response_data)
        self.assertEqual(response_data.get("message"), message)

    def positive_response_content_helper(
        self, response, expected_available_slots
    ):
        """Assert response contains expected available slots."""
        response_data = json.loads(response.content)
        self.assertIn("availableSlots", response_data)

        returned_slots = (
            response_data.get("availableSlots")
            if response_data.get("availableSlots")
            else []
        )
        self.assertEqual(len(returned_slots), len(expected_available_slots))

        return returned_slots

    def error_response_helper(self, response, expected_code, expected_message):
        """Assert error response."""
        self.assertEqual(response.status_code, expected_code)
        response_data = json.loads(response.content)
        self.assertIn("error", response_data)
        self.assertEqual(response_data.get("error"), expected_message)

    def setUp(self):
        super().setUp()
        self.slots_url = reverse("available_time_slots")
        self.class_one = ClassModel.objects.create(
            name="Foil", duration_minutes=60, school=self.school
        )
        self.class_two = ClassModel.objects.create(
            name="Heavy sabre", duration_minutes=90, school=self.school
        )
        self.day_one_name = "Monday"
        self.day_two_name = "Tuesday"
        self.day_one = Day.objects.create(name=self.day_one_name)
        self.day_two = Day.objects.create(name=self.day_two_name)
        self.time_one = "10:00:00"
        self.time_two = "15:30:00"
        self.schedule_one = Schedule.objects.create(
            class_model=self.class_one,
            day=self.day_two,
            class_time=parse_time(self.time_one),
            school=self.school,
        )
        self.schedule_two = Schedule.objects.create(
            class_model=self.class_two,
            day=self.day_two,
            class_time=parse_time(self.time_two),
            school=self.school,
        )

        self.new_class_duration = 60

        self.available_slots_day_one = [
            "08:00", "08:30", "09:00", "09:30",
            "10:00", "10:30", "11:00", "11:30",
            "12:00", "12:30", "13:00", "13:30",
            "14:00", "14:30", "15:00", "15:30",
            "16:00", "16:30", "17:00", "17:30",
            "18:00", "18:30", "19:00", "19:30",
            "20:00",
        ]
        self.available_slots_day_two = [
            "08:00", "08:30", "09:00", "11:00",
            "11:30", "12:00", "12:30", "13:00",
            "13:30", "14:00", "14:30", "17:00",
            "17:30", "18:00", "18:30",
            "19:00", "19:30", "20:00",
        ]

    def test_empty_day_has_all_available_intervals(self):
        response = self.client.get(
            self.slots_url, {"day": self.day_one_name, "duration": self.new_class_duration}
        )
        self.positive_response_helper(response, 200, "Available time slots")
        returned_slots = self.positive_response_content_helper(
            response, self.available_slots_day_one
        )

        for slot in self.available_slots_day_one:
            self.assertIn(slot, returned_slots)

    def test_busy_day_only_available_intervals(self):
        response = self.client.get(
            self.slots_url, {"day": self.day_two_name, "duration": self.new_class_duration}
        )
        self.positive_response_helper(response, 200, "Available time slots")
        returned_slots = self.positive_response_content_helper(
            response, self.available_slots_day_two
        )
        print(returned_slots)

        for slot in self.available_slots_day_two:
            self.assertIn(slot, returned_slots)
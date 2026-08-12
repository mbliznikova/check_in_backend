"""Tests for edit/delete operations across models."""
import json
from datetime import time

from django.urls import reverse
from django.utils.timezone import now

from ..models import (
    ClassModel, ClassOccurrence, Day, Payment, Schedule, Student,
)
from .test_utils import BaseTestCase


class StudentCRUDTestCase(BaseTestCase):
    """Tests for student edit/delete operations."""

    def setUp(self):
        super().setUp()
        self.student = Student.objects.create(
            first_name="Original", last_name="Student", school=self.school
        )
        self.student_detail_url = f"/api/students/{self.student.id}/"

    # TODO: Add tests for PATCH /students/<id>/
    # TODO: Add tests for DELETE /students/<id>/
    pass


class ClassCRUDTestCase(BaseTestCase):
    """Tests for class edit/delete operations."""

    def setUp(self):
        super().setUp()
        self.class_obj = ClassModel.objects.create(
            name="Test Class", school=self.school)
        self.edit_class_url = reverse(
            "edit_class", args=[self.class_obj.id])

    def test_patch_class_name_successfully(self):
        response = self.client.patch(
            self.edit_class_url,
            json.dumps({"name": "Updated Class"}),
            content_type="application/json",
        )
        self.positive_response_helper(
            response, 200, "Class was updated successfully")
        response_data = json.loads(response.content)
        self.assertEqual(response_data["className"], "Updated Class")
        self.class_obj.refresh_from_db()
        self.assertEqual(self.class_obj.name, "Updated Class")

    def test_patch_class_partial_update_leaves_other_fields_untouched(self):
        response = self.client.patch(
            self.edit_class_url,
            json.dumps({"durationMinutes": 90}),
            content_type="application/json",
        )
        self.positive_response_helper(
            response, 200, "Class was updated successfully")
        self.class_obj.refresh_from_db()
        self.assertEqual(self.class_obj.duration_minutes, 90)
        self.assertEqual(self.class_obj.name, "Test Class")
        self.assertTrue(self.class_obj.is_recurring)

    def test_patch_class_is_recurring(self):
        response = self.client.patch(
            self.edit_class_url,
            json.dumps({"isRecurring": False}),
            content_type="application/json",
        )
        self.positive_response_helper(
            response, 200, "Class was updated successfully")
        self.class_obj.refresh_from_db()
        self.assertFalse(self.class_obj.is_recurring)

    def test_patch_class_empty_name_validation(self):
        response = self.client.patch(
            self.edit_class_url,
            json.dumps({"name": "   "}),
            content_type="application/json",
        )
        self.error_response_helper(
            response, 400, "Class name cannot be empty")
        self.class_obj.refresh_from_db()
        self.assertEqual(self.class_obj.name, "Test Class")

    def test_patch_class_not_found(self):
        non_existent_id = 9999
        url = reverse("edit_class", args=[non_existent_id])
        response = self.client.patch(
            url,
            json.dumps({"name": "Doesn't matter"}),
            content_type="application/json",
        )
        self.error_response_helper(response, 404, "Class not found")

    def test_patch_class_invalid_json(self):
        response = self.client.patch(
            self.edit_class_url,
            "not valid json",
            content_type="application/json",
        )
        self.error_response_helper(response, 400, "Invalid JSON")

    def test_put_class_no_longer_allowed(self):
        response = self.client.put(
            self.edit_class_url,
            json.dumps({"name": "Should Not Work"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 405)

    # TODO: Add tests for DELETE /classes/<id>/


class ClassOccurrenceCRUDTestCase(BaseTestCase):
    """Tests for class occurrence edit/delete operations."""

    def setUp(self):
        super().setUp()
        self.class_model = ClassModel.objects.create(
            name="Test Class", school=self.school)
        self.occurrence = ClassOccurrence.objects.create(
            school=self.school,
            class_model=self.class_model,
            planned_date=now().date(),
            actual_date=now().date(),
            planned_start_time=time(10, 0),
            actual_start_time=time(10, 0),
            planned_duration=60,
            actual_duration=60,
        )
        self.occurrence_detail_url = f"/api/class_occurrences/{
            self.occurrence.id}/"

    # TODO: Add tests for PUT/PATCH /class_occurrences/<id>/
    # TODO: Add tests for DELETE /class_occurrences/<id>/
    pass


class ScheduleCRUDTestCase(BaseTestCase):
    """Tests for schedule delete operation."""

    def setUp(self):
        super().setUp()
        self.class_model = ClassModel.objects.create(
            name="Test Class", school=self.school)
        self.day, _ = Day.objects.get_or_create(name="Monday")
        self.schedule = Schedule.objects.create(
            class_model=self.class_model,
            day=self.day,
            class_time=time(10, 0),
            school=self.school,
        )
        self.schedule_detail_url = f"/api/schedules/{self.schedule.id}/"

    # TODO: Add tests for DELETE /schedules/<id>/
    pass


class PaymentCRUDTestCase(BaseTestCase):
    """Tests for payment delete operation."""

    def setUp(self):
        super().setUp()
        self.student = Student.objects.create(
            first_name="John", last_name="Doe", school=self.school
        )
        self.class_model = ClassModel.objects.create(
            name="Test Class", school=self.school)
        self.payment = Payment.objects.create(
            student_id=self.student,
            class_occurrence=None,  # or create a class occurrence
            fallback_class_id=self.class_model.id,
            class_name="Test Class",
            attendance_date=now().date(),
            school=self.school,
            amount=50.0,
            payment_month=7,
            payment_year=2025,
        )
        self.payment_detail_url = f"/api/payments/{self.payment.id}/"

    # TODO: Add tests for DELETE /payments/<id>/
    pass

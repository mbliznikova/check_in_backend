"""Tests for edit/delete operations across models."""
import json
from datetime import time

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
        self.class_detail_url = f"/api/classes/{self.class_obj.id}/"

    # TODO: Add tests for PATCH /classes/<id>/
    # TODO: Add tests for DELETE /classes/<id>/
    pass


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
        self.day = Day.objects.create(name="Monday")
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

"""Tests for attendance confirmation functionality."""
import json
from datetime import datetime, time

from django.urls import reverse
from django.utils.timezone import now

from ..models import Attendance, ClassModel, ClassOccurrence, Student
from .test_utils import BaseTestCase


class ConfirmTestCase(BaseTestCase):
    """Tests for the confirm endpoint (PUT /confirm/)."""

    def setUp(self):
        super().setUp()
        self.confirm_url = reverse("confirm")

        self.test_student = Student.objects.create(
            first_name="John", last_name="Testovich", school=self.school
        )
        self.class_one = ClassModel.objects.create(
            name="Rapier and dagger", school=self.school)
        self.class_two = ClassModel.objects.create(
            name="Self-defence", school=self.school)
        self.class_three = ClassModel.objects.create(
            name="Longsword", school=self.school)

        self.today_date = now().date()
        self.today = self.today_date.isoformat()
        self.another_date = datetime(2025, 5, 13).date()

        # Create occurrences
        self.occurrence_one = ClassOccurrence.objects.create(
            school=self.school,
            class_model=self.class_one,
            planned_date=self.today_date,
            actual_date=self.today_date,
            planned_start_time=time(10, 0),
            actual_start_time=time(10, 0),
            planned_duration=60,
            actual_duration=60,
        )
        self.occurrence_two = ClassOccurrence.objects.create(
            school=self.school,
            class_model=self.class_two,
            planned_date=self.today_date,
            actual_date=self.today_date,
            planned_start_time=time(10, 0),
            actual_start_time=time(10, 0),
            planned_duration=60,
            actual_duration=60,
        )
        self.occurrence_three = ClassOccurrence.objects.create(
            school=self.school,
            class_model=self.class_three,
            planned_date=self.another_date,
            actual_date=self.another_date,
            planned_start_time=time(10, 0),
            actual_start_time=time(10, 0),
            planned_duration=60,
            actual_duration=60,
        )

        # Create attendance records
        self.attendance_one = Attendance.objects.create(
            student_id=self.test_student,
            class_occurrence=self.occurrence_one,
            attendance_date=self.today,
            school=self.school,
        )
        self.attendance_two = Attendance.objects.create(
            student_id=self.test_student,
            class_occurrence=self.occurrence_two,
            attendance_date=self.today,
            school=self.school,
        )
        self.attendance_three = Attendance.objects.create(
            student_id=self.test_student,
            class_occurrence=self.occurrence_three,
            attendance_date=self.another_date,
            school=self.school,
        )

    def test_student_checked_not_today_datetime(self):
        request_data = {
            "confirmationList": [
                {self.test_student.id: {self.occurrence_three.id: True}}
            ],
            "date": "2025-05-13",
        }

        response = self.client.put(
            self.confirm_url,
            json.dumps(request_data),
            content_type="application/json")
        self.positive_response_helper(
            response, 200, "Attendance confirmed successfully")

        attendance_records = Attendance.objects.filter(
            student_id=self.test_student, attendance_date=self.another_date
        )
        self.assertEqual(len(attendance_records), 1)
        self.assertIn(self.attendance_three, attendance_records)
        self.assertEqual(
            attendance_records[0].attendance_date,
            self.another_date)

    def test_student_checked_no_datetime_provided(self):
        request_data = {
            "confirmationList": [
                {self.test_student.id: {self.occurrence_one.id: True}}
            ]
        }

        response = self.client.put(
            self.confirm_url,
            json.dumps(request_data),
            content_type="application/json")
        self.positive_response_helper(
            response, 200, "Attendance confirmed successfully")

        attendance_records = Attendance.objects.filter(
            student_id=self.test_student, attendance_date=self.today_date
        )
        self.assertEqual(len(attendance_records), 1)
        self.assertIn(self.attendance_one, attendance_records)
        self.assertEqual(
            attendance_records[0].attendance_date.isoformat(),
            self.today)

    def test_student_checked_confirmed(self):
        request_data = {
            "confirmationList": [
                {
                    self.test_student.id: {
                        self.occurrence_one.id: True,
                        self.occurrence_two.id: True,
                    }
                }
            ]
        }

        response = self.client.put(
            self.confirm_url,
            json.dumps(request_data),
            content_type="application/json")
        self.positive_response_helper(
            response, 200, "Attendance confirmed successfully")

        attendance_records = Attendance.objects.filter(
            student_id=self.test_student, attendance_date=self.today_date
        )
        self.assertEqual(len(attendance_records), 2)
        self.assertIn(self.attendance_one, attendance_records)
        self.assertIn(self.attendance_two, attendance_records)
        for record in attendance_records:
            self.assertEqual(record.is_showed_up, True)

    def test_student_unchecked_24_hrs_policy(self):
        request_data = {"confirmationList": [{self.test_student.id: {
            self.occurrence_one.id: False, self.occurrence_two.id: False}}]}

        response = self.client.put(
            self.confirm_url,
            json.dumps(request_data),
            content_type="application/json")
        self.positive_response_helper(
            response, 200, "Attendance confirmed successfully")

        attendance_records = Attendance.objects.filter(
            student_id=self.test_student, attendance_date=self.today_date
        )
        self.assertEqual(len(attendance_records), 2)
        self.assertIn(self.attendance_one, attendance_records)
        self.assertIn(self.attendance_two, attendance_records)
        for record in attendance_records:
            self.assertEqual(record.is_showed_up, False)

    def test_student_unchecked_no_24_hrs_policy(self):
        request_data = {
            "confirmationList": [{self.test_student.id: {}}]
        }

        response = self.client.put(
            self.confirm_url,
            json.dumps(request_data),
            content_type="application/json")
        self.positive_response_helper(
            response, 200, "Attendance confirmed successfully")

        attendance_records = Attendance.objects.filter(
            student_id=self.test_student, attendance_date=self.today_date
        )
        self.assertEqual(len(attendance_records), 0)

    def test_student_checked_one_class_and_unchecked_another_no_24_hrs_policy(
            self):
        request_data = {
            "confirmationList": [
                {self.test_student.id: {self.occurrence_one.id: True}}
            ]
        }

        response = self.client.put(
            self.confirm_url,
            json.dumps(request_data),
            content_type="application/json")
        self.positive_response_helper(
            response, 200, "Attendance confirmed successfully")

        attendance_records = Attendance.objects.filter(
            student_id=self.test_student, attendance_date=self.today_date
        )
        self.assertEqual(len(attendance_records), 1)
        self.assertIn(self.attendance_one, attendance_records)
        self.assertEqual(
            attendance_records[0].class_occurrence.id,
            self.occurrence_one.id)

    def test_student_checked_one_class_no_24_hrs_policy_and_unchecked_another_24_hrs_policy(
            self):
        request_data = {
            "confirmationList": [
                {
                    self.test_student.id: {
                        self.occurrence_one.id: True,
                        self.occurrence_two.id: False,
                    }
                }
            ]
        }

        response = self.client.put(
            self.confirm_url,
            json.dumps(request_data),
            content_type="application/json")
        self.positive_response_helper(
            response, 200, "Attendance confirmed successfully")

        attendance_records = Attendance.objects.filter(
            student_id=self.test_student, attendance_date=self.today_date
        )
        self.assertEqual(len(attendance_records), 2)
        self.assertIn(self.attendance_one, attendance_records)
        self.assertIn(self.attendance_two, attendance_records)
        for record in attendance_records:
            if record.class_occurrence.id == self.occurrence_one.id:
                self.assertEqual(record.is_showed_up, True)
            if record.class_occurrence.id == self.occurrence_two.id:
                self.assertEqual(record.is_showed_up, False)

    def test_student_unchecked_one_class_no_24_hrs_policy_and_unchecked_another_24_hrs_policy(
            self):
        request_data = {
            "confirmationList": [
                {self.test_student.id: {self.occurrence_two.id: False}}
            ]
        }

        response = self.client.put(
            self.confirm_url,
            json.dumps(request_data),
            content_type="application/json")
        self.positive_response_helper(
            response, 200, "Attendance confirmed successfully")

        attendance_records = Attendance.objects.filter(
            student_id=self.test_student, attendance_date=self.today_date
        )
        self.assertEqual(len(attendance_records), 1)
        self.assertIn(self.attendance_two, attendance_records)
        self.assertEqual(
            attendance_records[0].class_occurrence.id,
            self.occurrence_two.id)

    def test_invalid_json(self):
        response = self.client.put(
            self.confirm_url,
            data="invalid JSON",
            content_type="application/json")
        self.assertEqual(response.status_code, 400)

        response_data = json.loads(response.content)
        self.assertIn("error", response_data)
        self.assertEqual(response_data.get("error"), "Invalid JSON")

    def test_invalid_data_format_confirmation_list_is_no_list(self):
        request_data = {"confirmationList": {}}

        response = self.client.put(
            self.confirm_url,
            json.dumps(request_data),
            content_type="application/json")
        self.assertEqual(response.status_code, 400)

        response_data = json.loads(response.content)
        self.assertIn("error", response_data)
        self.assertEqual(
            response_data.get("error"),
            "Invalid data format: 'confirmationList' should be a list",
        )

    def test_invalid_data_format_no_dicts_in_confirmation_list(self):
        request_data = {
            "confirmationList": [
                [self.test_student.id, [self.occurrence_one.id, self.occurrence_two.id]],
            ]
        }

        response = self.client.put(
            self.confirm_url,
            json.dumps(request_data),
            content_type="application/json")
        self.assertEqual(response.status_code, 400)

        response_data = json.loads(response.content)
        self.assertIn("error", response_data)
        self.assertEqual(
            response_data.get("error"),
            "Invalid data format: Each item in 'confirmationList' should be a dictionary",
        )

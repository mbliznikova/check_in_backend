"""Tests for check-in functionality."""
import json
from datetime import time

from django.test import TestCase
from django.urls import reverse
from django.utils.timezone import now

from ..models import ClassModel, Student, Attendance, ClassOccurrence
from .test_utils import BaseTestCase


class CheckInTestCase(BaseTestCase):
    """Tests for the check-in endpoint (POST /check_in/)."""

    def positive_response_content_helper(
        self, response, expected_checked_in_list=None, expected_checked_out_list=None
    ):
        """Assert response contains correct student ID, attendance date, and checked in/out lists."""
        response_data = json.loads(response.content)
        self.assertIn("studentId", response_data)
        self.assertEqual(response_data.get("studentId"), self.test_student.id)
        self.assertIn("attendanceDate", response_data)
        self.assertEqual(response_data.get("attendanceDate"), self.today)

        if expected_checked_in_list:
            self.assertIn("checkedIn", response_data)
            self.assertEqual(len(response_data.get("checkedIn")), len(expected_checked_in_list))
            self.assertEqual(set(response_data.get("checkedIn")), set(expected_checked_in_list))
        if expected_checked_out_list:
            self.assertIn("checkedOut", response_data)
            self.assertEqual(len(response_data.get("checkedOut")), len(expected_checked_out_list))
            self.assertEqual(set(response_data.get("checkedOut")), set(expected_checked_out_list))

    def setUp(self):
        super().setUp()
        self.check_in_url = reverse("check_in")

        self.test_student = Student.objects.create(
            first_name="John", last_name="Testovich", school=self.school
        )
        self.class_one = ClassModel.objects.create(name="Foil", school=self.school)
        self.class_two = ClassModel.objects.create(name="Heavy sabre", school=self.school)

        # Use date object for occurrences
        self.today_date = now().date()
        self.today = self.today_date.isoformat()

        # Create class occurrences
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

    def test_student_checks_in(self):
        request_data = {
            "checkInData": {
                "studentId": self.test_student.id,
                "classOccurrencesList": [self.occurrence_one.id],
                "todayDate": self.today,
            }
        }

        response = self.client.post(
            self.check_in_url,
            json.dumps(request_data),
            content_type="application/json",
        )
        # Debug: print response content if not 200
        if response.status_code != 200:
            print("Response status:", response.status_code)
            print("Response content:", response.content.decode())
        self.positive_response_helper(response, 200, "Check-in data was successfully updated")
        self.positive_response_content_helper(
            response=response, expected_checked_in_list=[self.occurrence_one.id]
        )

        attendance_record = Attendance.objects.filter(
            student_id=self.test_student, attendance_date=self.today
        )
        self.assertEqual(attendance_record.count(), 1)

    def test_student_checks_in_multiple_classes(self):
        request_data = {
            "checkInData": {
                "studentId": self.test_student.id,
                "classOccurrencesList": [self.occurrence_one.id, self.occurrence_two.id],
                "todayDate": self.today,
            }
        }

        response = self.client.post(
            self.check_in_url,
            json.dumps(request_data),
            content_type="application/json",
        )
        self.positive_response_helper(response, 200, "Check-in data was successfully updated")
        self.positive_response_content_helper(
            response=response, expected_checked_in_list=[self.occurrence_one.id, self.occurrence_two.id]
        )

        attendance_record = Attendance.objects.filter(
            student_id=self.test_student, attendance_date=self.today
        )
        self.assertEqual(attendance_record.count(), 2)

    def test_student_checks_out(self):
        Attendance.objects.create(
            student_id=self.test_student,
            class_occurrence=self.occurrence_one,
            attendance_date=self.today,
            school=self.school,
        )
        attendance_initial_record = Attendance.objects.filter(
            student_id=self.test_student, attendance_date=self.today
        )
        self.assertEqual(attendance_initial_record.count(), 1)

        request_data = {
            "checkInData": {
                "studentId": self.test_student.id,
                "classOccurrencesList": [],
                "todayDate": self.today,
            }
        }

        response = self.client.post(
            self.check_in_url,
            json.dumps(request_data),
            content_type="application/json",
        )
        self.positive_response_helper(response, 200, "Check-in data was successfully updated")
        self.positive_response_content_helper(
            response=response, expected_checked_out_list=[self.occurrence_one.id]
        )

        attendance_final_record = list(
            Attendance.objects.filter(student_id=self.test_student, attendance_date=self.today)
            .values_list("class_occurrence", flat=True)
        )
        self.assertEqual(len(attendance_final_record), 0)

    def test_student_checks_in_one_class_checks_out_another_class(self):
        Attendance.objects.create(
            student_id=self.test_student,
            class_occurrence=self.occurrence_one,
            attendance_date=self.today,
            school=self.school,
        )
        attendance_initial_record = list(
            Attendance.objects.filter(student_id=self.test_student, attendance_date=self.today)
            .values_list("class_occurrence", flat=True)
        )
        self.assertEqual(len(attendance_initial_record), 1)
        self.assertEqual(attendance_initial_record[0], self.occurrence_one.id)

        request_data = {
            "checkInData": {
                "studentId": self.test_student.id,
                "classOccurrencesList": [self.occurrence_two.id],
                "todayDate": self.today,
            }
        }

        response = self.client.post(
            self.check_in_url,
            json.dumps(request_data),
            content_type="application/json",
        )
        self.positive_response_helper(response, 200, "Check-in data was successfully updated")
        self.positive_response_content_helper(
            response=response,
            expected_checked_in_list=[self.occurrence_two.id],
            expected_checked_out_list=[self.occurrence_one.id],
        )

        attendance_final_record = list(
            Attendance.objects.filter(student_id=self.test_student, attendance_date=self.today)
            .values_list("class_occurrence", flat=True)
        )
        self.assertEqual(len(attendance_final_record), 1)
        self.assertEqual(attendance_final_record[0], self.occurrence_two.id)

    def test_missing_required_field(self):
        request_data = {
            "checkInData": {
                "studentId": self.test_student.id,
                "classesList": [self.class_two.id],
            }
        }

        response = self.client.post(
            self.check_in_url,
            json.dumps(request_data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = json.loads(response.content)
        self.assertIn("error", response_data)
        self.assertEqual(response_data.get("error"), "Missing required fields")

    def test_invalid_json(self):
        response = self.client.post(
            self.check_in_url, data="invalid JSON", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

        response_data = json.loads(response.content)
        self.assertIn("error", response_data)
        self.assertEqual(response_data.get("error"), "Invalid JSON")
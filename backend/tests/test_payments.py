"""Tests for payment functionality."""
import json
from datetime import datetime

from django.urls import reverse
from django.utils.timezone import now

from ..models import ClassModel, Payment, Student
from .test_utils import BaseTestCase


class PaymentTestCase(BaseTestCase):
    """Tests for the payments endpoint (POST /payments/)."""

    def base_positive_response_content_helper(self, response_data):
        """Assert common fields in successful payment response."""
        self.assertIn("paymentId", response_data)
        self.assertIn("studentId", response_data)
        self.assertEqual(response_data.get("studentId"), self.test_student.id)
        self.assertIn("classId", response_data)
        self.assertEqual(response_data.get("classId"), self.class_one.id)
        self.assertIn("amount", response_data)
        self.assertTrue(isinstance(response_data.get("amount"), (int, float)))
        self.assertIn("paymentMonth", response_data)
        self.assertIn("paymentYear", response_data)

    def additional_positive_response_content_helper(self, response_data):
        """Assert additional fields in successful payment response."""
        self.assertIn("studentName", response_data)
        student_name = f"{
            self.test_student.first_name} {
            self.test_student.last_name}"
        self.assertEqual(response_data.get("studentName"), student_name)

        self.assertIn("className", response_data)
        class_name = self.class_one.name
        self.assertEqual(response_data.get("className"), class_name)

        self.assertIn("paymentDate", response_data)
        payment_date = datetime.fromisoformat(response_data.get("paymentDate"))
        expected_date = self.today
        self.assertEqual(payment_date.year, expected_date.year)
        self.assertEqual(payment_date.month, expected_date.month)

    def get_response_data_helper(self, response):
        """Parse response JSON and return data."""
        response_data = json.loads(response.content)
        return response_data

    def base_positive_validation(self, request_data):
        """Helper to validate successful payment creation."""
        # Ensure school is included in paymentData
        if "paymentData" in request_data:
            request_data["paymentData"]["school"] = self.school.id
        response = self.client.post(
            self.payments_url,
            json.dumps(request_data),
            content_type="application/json",
        )
        self.positive_response_helper(
            response, 200, "Payment was successfully created")

        response_data = self.get_response_data_helper(response)
        self.base_positive_response_content_helper(response_data)
        self.additional_positive_response_content_helper(response_data)

        payment_record_id = Payment.objects.get(
            id=response_data.get("paymentId"))
        self.assertEqual(payment_record_id.id, response_data.get("paymentId"))

    def base_negative_validation_invalid_request_fields(
        self, request_data, status_code, error_message
    ):
        """Helper to validate error responses for invalid payment data."""
        if "paymentData" in request_data:
            request_data["paymentData"]["school"] = self.school.id
        response = self.client.post(
            self.payments_url,
            json.dumps(request_data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status_code)

        response_data = self.get_response_data_helper(response)
        self.assertIn("error", response_data)
        self.assertEqual(response_data.get("error"), error_message)

    def setUp(self):
        super().setUp()
        self.payments_url = reverse("payments")

        self.test_student = Student.objects.create(
            first_name="John", last_name="Testovich", school=self.school
        )
        self.class_one = ClassModel.objects.create(
            name="Foil", school=self.school)

        # Django may internally convert isoformat string back into a naive datetime if it's missing timezone info
        # To be safe, it's better to store the actual aware datetime object,
        # not the string
        # have an object, not str, with timezone included, convert to string
        # later
        self.today = now()
        # have a naive object, without timezone included, convert to string
        # later
        self.today_naive = datetime.now()

    def test_successful_payment_made(self):
        request_data = {
            "paymentData": {
                "studentId": self.test_student.id,
                "classId": self.class_one.id,
                "studentName": "John Testovich",
                "className": "Foil",
                "amount": 50.0,
                "paymentDate": self.today.isoformat(),
                "month": 7,
                "year": 2025,
            }
        }

        self.base_positive_validation(request_data)

    def test_successful_payment_made_naive_payment_date(self):
        request_data = {
            "paymentData": {
                "studentId": self.test_student.id,
                "classId": self.class_one.id,
                "studentName": "John Testovich",
                "className": "Foil",
                "amount": 50.0,
                "paymentDate": self.today_naive.isoformat(),
                "month": 7,
                "year": 2025,
            }
        }

        self.base_positive_validation(request_data)

    def test_successful_payment_made_no_student_name(self):
        request_data = {
            "paymentData": {
                "studentId": self.test_student.id,
                "classId": self.class_one.id,
                "studentName": "",
                "className": "Foil",
                "amount": 50.0,
                "paymentDate": self.today.isoformat(),
                "month": 7,
                "year": 2025,
            }
        }

        self.base_positive_validation(request_data)

    def test_successful_payment_made_no_class_name(self):
        request_data = {
            "paymentData": {
                "studentId": self.test_student.id,
                "classId": self.class_one.id,
                "studentName": "John Testovich",
                "className": "",
                "amount": 50.0,
                "paymentDate": self.today.isoformat(),
                "month": 7,
                "year": 2025,
            }
        }

        self.base_positive_validation(request_data)

    def test_successful_payment_made_no_payment_date(self):
        request_data = {
            "paymentData": {
                "studentId": self.test_student.id,
                "classId": self.class_one.id,
                "studentName": "John Testovich",
                "className": "",
                "amount": 50.0,
                "month": 7,
                "year": 2025,
            }
        }

        self.base_positive_validation(request_data)

    def test_invalid_payment_missing_student_id(self):
        request_data = {
            "paymentData": {
                "studentId": None,
                "classId": self.class_one.id,
                "studentName": "John Testovich",
                "className": "",
                "amount": 50.0,
                "paymentDate": self.today.isoformat(),
                "month": 7,
                "year": 2025,
            }
        }

        self.base_negative_validation_invalid_request_fields(
            request_data, 400, "Missing required fields"
        )

    def test_invalid_payment_missing_class_id(self):
        request_data = {
            "paymentData": {
                "studentId": self.test_student.id,
                "classId": None,
                "studentName": "John Testovich",
                "className": "",
                "amount": 50.0,
                "paymentDate": self.today.isoformat(),
                "month": 7,
                "year": 2025,
            }
        }

        self.base_negative_validation_invalid_request_fields(
            request_data, 400, "Missing required fields"
        )

    def test_invalid_payment_invalid_datetime_format(self):
        request_data = {
            "paymentData": {
                "studentId": self.test_student.id,
                "classId": self.class_one.id,
                "studentName": "John Testovich",
                "className": "",
                "amount": 50.0,
                "paymentDate": "2025-02-01-00-00-00",
                "month": 7,
                "year": 2025,
            }
        }

        self.base_negative_validation_invalid_request_fields(
            request_data, 400, "Invalid datetime format for payment date"
        )

    def test_invalid_payment_no_month_no_year(self):
        request_data = {
            "paymentData": {
                "studentId": self.test_student.id,
                "classId": self.class_one.id,
                "studentName": "John Testovich",
                "className": "",
                "amount": 50.0,
                "paymentDate": self.today.isoformat(),
                "month": None,
                "year": None,
            }
        }

        self.base_negative_validation_invalid_request_fields(
            request_data, 400, "Missing required fields"
        )

    def test_invalid_payment_text_month_format(self):
        request_data = {
            "paymentData": {
                "studentId": self.test_student.id,
                "classId": self.class_one.id,
                "studentName": "John Testovich",
                "className": "",
                "amount": 50.0,
                "paymentDate": self.today.isoformat(),
                "month": "Jul",
                "year": 2025,
            }
        }

        self.base_negative_validation_invalid_request_fields(
            request_data, 400, "Invalid date format for month or year"
        )

    def test_invalid_payment_month_value_out_of_range(self):
        request_data = {
            "paymentData": {
                "studentId": self.test_student.id,
                "classId": self.class_one.id,
                "studentName": "John Testovich",
                "className": "",
                "amount": 50.0,
                "paymentDate": self.today.isoformat(),
                "month": 13,
                "year": 2025,
            }
        }

        self.base_negative_validation_invalid_request_fields(
            request_data, 400, "Invalid value for month: should be between 1 and 12")

    def test_retrieving_payments_from_another_month(self):
        another_payment_month = 6

        request_data_one = {
            "paymentData": {
                "studentId": self.test_student.id,
                "classId": self.class_one.id,
                "studentName": "John Testovich",
                "className": "Foil",
                "amount": 50.0,
                "month": 7,
                "year": 2025,
            }
        }

        request_data_two = {
            "paymentData": {
                "studentId": self.test_student.id,
                "classId": self.class_one.id,
                "studentName": "John Testovich",
                "className": "Foil",
                "amount": 50.0,
                "month": another_payment_month,
                "year": 2025,
            }
        }

        self.base_positive_validation(request_data_one)
        self.base_positive_validation(request_data_two)

        all_payments = Payment.objects.all()
        self.assertEqual(all_payments.count(), 2)
        payment_record_for_another_month = Payment.objects.filter(
            payment_month=another_payment_month
        )
        self.assertEqual(payment_record_for_another_month.count(), 1)

    def test_retrieving_payments_from_another_year(self):
        another_payment_year = 2024

        request_data_one = {
            "paymentData": {
                "studentId": self.test_student.id,
                "classId": self.class_one.id,
                "studentName": "John Testovich",
                "className": "Foil",
                "amount": 50.0,
                "month": 7,
                "year": 2025,
            }
        }

        request_data_two = {
            "paymentData": {
                "studentId": self.test_student.id,
                "classId": self.class_one.id,
                "studentName": "John Testovich",
                "className": "Foil",
                "amount": 50.0,
                "month": 7,
                "year": another_payment_year,
            }
        }

        self.base_positive_validation(request_data_one)
        self.base_positive_validation(request_data_two)

        all_payments = Payment.objects.all()
        self.assertEqual(all_payments.count(), 2)
        payment_record_for_another_month = Payment.objects.filter(
            payment_year=another_payment_year
        )
        self.assertEqual(payment_record_for_another_month.count(), 1)

import json

from datetime import datetime, time

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils.dateparse import parse_time
from django.utils.timezone import now

from .models import ClassModel, Student, Attendance, Payment, Day, Schedule

class CheckInTestCase(TestCase):
    def positive_response_helper(self, response, expected_status, message):
        self.assertEqual(response.status_code, expected_status)
        response_data = json.loads(response.content)
        self.assertIn("message", response_data)
        self.assertEqual(response_data.get("message"), message)

    def positive_response_content_helper(self, response, expected_checked_in_list=None, expected_checked_out_list=None):
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
        self.test_student = Student.objects.create(first_name="John", last_name="Testovich")
        self.class_one = ClassModel.objects.create(name="Foil")
        self.class_two = ClassModel.objects.create(name="Heavy sabre")

        self.today = now().date().isoformat()

        self.check_in_url = reverse("check_in")

    def test_student_checks_in(self):
        request_data = {
            "checkInData": {
                "studentId": self.test_student.id,
                "classesList": [self.class_one.id],
                "todayDate": self.today,
            }
        }

        response = self.client.post(self.check_in_url, json.dumps(request_data), content_type="application/json")
        self.positive_response_helper(response, 200, "Check-in data was successfully updated")
        self.positive_response_content_helper(response=response, expected_checked_in_list=[self.class_one.id])

        attendance_record = Attendance.objects.filter(student_id=self.test_student, attendance_date=self.today)
        self.assertEqual(attendance_record.count(), 1)

    def test_student_checks_in_multiple_classes(self):
        request_data = {
            "checkInData": {
                "studentId": self.test_student.id,
                "classesList": [self.class_one.id, self.class_two.id],
                "todayDate": self.today,
            }
        }

        response = self.client.post(self.check_in_url, json.dumps(request_data), content_type="application/json")
        self.positive_response_helper(response, 200, "Check-in data was successfully updated")
        self.positive_response_content_helper(response=response, expected_checked_in_list=[self.class_one.id, self.class_two.id])

        attendance_record = Attendance.objects.filter(student_id=self.test_student, attendance_date=self.today)
        self.assertEqual(attendance_record.count(), 2)

    def test_student_checks_out(self):
        Attendance.objects.create(student_id=self.test_student, class_id=self.class_one, attendance_date=self.today)
        attendance_initial_record = Attendance.objects.filter(student_id=self.test_student, attendance_date=self.today)
        self.assertEqual(attendance_initial_record.count(), 1)

        request_data = {
            "checkInData": {
                "studentId": self.test_student.id,
                "classesList": [],
                "todayDate": self.today,
            }
        }

        response = self.client.post(self.check_in_url, json.dumps(request_data), content_type="application/json")
        self.positive_response_helper(response, 200, "Check-in data was successfully updated")
        self.positive_response_content_helper(response=response, expected_checked_out_list=[self.class_one.id])

        attendance_final_record = Attendance.objects.filter(student_id=self.test_student, attendance_date=self.today)
        self.assertEqual(attendance_final_record.count(), 0)

    def test_student_checks_in_one_class_checks_out_another_class(self):
        Attendance.objects.create(student_id=self.test_student, class_id=self.class_one, attendance_date=self.today)
        attendance_initial_record = list(Attendance.objects.filter(student_id=self.test_student, attendance_date=self.today).values_list("class_id", flat=True))
        self.assertEqual(len(attendance_initial_record), 1)
        self.assertEqual(attendance_initial_record[0], self.class_one.id)

        request_data = {
            "checkInData": {
                "studentId": self.test_student.id,
                "classesList": [self.class_two.id],
                "todayDate": self.today,
            }
        }

        response = self.client.post(self.check_in_url, json.dumps(request_data), content_type="application/json")
        self.positive_response_helper(response, 200, "Check-in data was successfully updated")
        self.positive_response_content_helper(response=response, expected_checked_in_list=[self.class_two.id], expected_checked_out_list=[self.class_one.id])

        attendance_final_record = list(Attendance.objects.filter(student_id=self.test_student, attendance_date=self.today).values_list("class_id", flat=True))
        self.assertEqual(len(attendance_final_record), 1)
        self.assertEqual(attendance_final_record[0], self.class_two.id)

    def test_missing_required_field(self):
        request_data = {
            "checkInData": {
                "studentId": self.test_student.id,
                "classesList": [self.class_two.id],
            }
        }

        response = self.client.post(self.check_in_url, json.dumps(request_data), content_type="application/json")
        self.assertEqual(response.status_code, 400)

        response_data = json.loads(response.content)
        self.assertIn("error", response_data)
        self.assertEqual(response_data.get("error"), "Missing required fields")

    def test_invalid_json(self):
        response = self.client.post(self.check_in_url, data="invalid JSON", content_type="application/json")
        self.assertEqual(response.status_code, 400)

        response_data = json.loads(response.content)
        self.assertIn("error", response_data)
        self.assertEqual(response_data.get("error"), "Invalid JSON")

class ConfirmTestCase(TestCase):
        # TODO: have a common positive_response_helper for each class?
        def positive_response_helper(self, response, expected_status, message):
            self.assertEqual(response.status_code, expected_status)
            response_data = json.loads(response.content)
            self.assertIn("message", response_data)
            self.assertEqual(response_data.get("message"), message)

        def setUp(self):
            self.test_student = Student.objects.create(first_name="John", last_name="Testovich")
            self.class_one = ClassModel.objects.create(name="Rapier and dagger")
            self.class_two = ClassModel.objects.create(name="Self-defence")
            self.class_three = ClassModel.objects.create(name="Longsword")

            self.today = now().date().isoformat()
            self.another_date = datetime(2025, 5, 13).date()

            self.attendance_one = Attendance.objects.create(student_id=self.test_student, class_id=self.class_one, attendance_date=self.today)
            self.attendance_two = Attendance.objects.create(student_id=self.test_student, class_id=self.class_two, attendance_date=self.today)
            self.attendance_three = Attendance.objects.create(student_id=self.test_student, class_id=self.class_three, attendance_date=self.another_date)

            self.confirm_url = reverse("confirm")

        def test_student_checked_not_today_datetime(self):
            request_data = {
                "confirmationList": [
                        {self.test_student.id: {
                            self.class_three.id: True
                        }}
                    ],
                "date": "2025-05-13",
            }

            response = self.client.put(self.confirm_url, json.dumps(request_data), content_type="application/json")
            self.positive_response_helper(response, 200, "Attendance confirmed successfully")

            attendance_records = Attendance.objects.filter(student_id=self.test_student, attendance_date=self.another_date)
            self.assertEqual(len(attendance_records), 1)
            self.assertIn(self.attendance_three, attendance_records)
            self.assertEqual(attendance_records[0].attendance_date, self.another_date)

        def test_student_checked_no_datetime_provided(self):
            request_data = {
                "confirmationList": [
                        {self.test_student.id: {
                            self.class_one.id: True
                        }}
                    ],
            }

            response = self.client.put(self.confirm_url, json.dumps(request_data), content_type="application/json")
            self.positive_response_helper(response, 200, "Attendance confirmed successfully")

            attendance_records = Attendance.objects.filter(student_id=self.test_student, attendance_date=self.today)
            self.assertEqual(len(attendance_records), 1)
            self.assertIn(self.attendance_one, attendance_records)
            self.assertEqual(attendance_records[0].attendance_date.isoformat(), self.today)

        def test_student_checked_confirmed(self):
            request_data = {
                "confirmationList": [
                        {self.test_student.id: {
                            self.class_one.id: True,
                            self.class_two.id: True
                        }}
                    ]
            }

            response = self.client.put(self.confirm_url, json.dumps(request_data), content_type="application/json")
            self.positive_response_helper(response, 200, "Attendance confirmed successfully")

            attendance_records = Attendance.objects.filter(student_id=self.test_student, attendance_date=self.today)
            self.assertEqual(len(attendance_records), 2)
            self.assertIn(self.attendance_one, attendance_records)
            self.assertIn(self.attendance_two, attendance_records)
            for record in attendance_records:
                self.assertEqual(record.is_showed_up, True)

        def test_student_unchecked_24_hrs_policy(self):
            request_data = {
                "confirmationList": [
                        {self.test_student.id: {
                            self.class_one.id: False,
                            self.class_two.id: False
                        }}
                    ]
            }

            response = self.client.put(self.confirm_url, json.dumps(request_data), content_type="application/json")
            self.positive_response_helper(response, 200, "Attendance confirmed successfully")

            attendance_records = Attendance.objects.filter(student_id=self.test_student, attendance_date=self.today)
            self.assertEqual(len(attendance_records), 2)
            self.assertIn(self.attendance_one, attendance_records)
            self.assertIn(self.attendance_two, attendance_records)
            for record in attendance_records:
                self.assertEqual(record.is_showed_up, False)

        def test_student_unchecked_no_24_hrs_policy(self):
            request_data = {
                "confirmationList": [
                        {self.test_student.id: {}}
                    ]
            }

            response = self.client.put(self.confirm_url, json.dumps(request_data), content_type="application/json")
            self.positive_response_helper(response, 200, "Attendance confirmed successfully")

            attendance_records = Attendance.objects.filter(student_id=self.test_student, attendance_date=self.today)
            self.assertEqual(len(attendance_records), 0)

        def test_student_checked_one_class_no_24_hrs_policy_and_unchecked_another_24_hrs_policy(self):
            request_data = {
                "confirmationList": [
                        {self.test_student.id: {
                            self.class_one.id: True,
                            self.class_two.id: False
                        }}
                    ]
            }

            response = self.client.put(self.confirm_url, json.dumps(request_data), content_type="application/json")
            self.positive_response_helper(response, 200, "Attendance confirmed successfully")

            attendance_records = Attendance.objects.filter(student_id=self.test_student, attendance_date=self.today)
            self.assertEqual(len(attendance_records), 2)
            self.assertIn(self.attendance_one, attendance_records)
            self.assertIn(self.attendance_two, attendance_records)
            for record in attendance_records:
                if record.class_id == self.class_one.id:
                    self.assertEqual(record.is_showed_up, True)
                if record.class_id == self.class_two.id:
                    self.assertEqual(record.is_showed_up, False)

        def test_student_unchecked_one_class_no_24_hrs_policy_and_unchecked_another_24_hrs_policy(self):
            request_data = {
                "confirmationList": [
                        {self.test_student.id: {
                            self.class_two.id: False
                        }}
                    ]
            }

            response = self.client.put(self.confirm_url, json.dumps(request_data), content_type="application/json")
            self.positive_response_helper(response, 200, "Attendance confirmed successfully")

            attendance_records = Attendance.objects.filter(student_id=self.test_student, attendance_date=self.today)
            self.assertEqual(len(attendance_records), 1)
            self.assertIn(self.attendance_two, attendance_records)
            self.assertEqual(attendance_records[0].class_id.id, self.class_two.id)
            self.assertEqual(attendance_records[0].is_showed_up, False)

        def test_student_checked_one_class_and_unchecked_another_no_24_hrs_policy(self):
            request_data = {
                "confirmationList": [
                        {self.test_student.id: {
                            self.class_one.id: True,
                        }}
                    ]
            }

            response = self.client.put(self.confirm_url, json.dumps(request_data), content_type="application/json")
            self.positive_response_helper(response, 200, "Attendance confirmed successfully")

            attendance_records = Attendance.objects.filter(student_id=self.test_student, attendance_date=self.today)
            self.assertEqual(len(attendance_records), 1)
            self.assertIn(self.attendance_one, attendance_records)
            self.assertEqual(attendance_records[0].class_id.id, self.class_one.id)

        def test_invalid_json(self):
            response = self.client.put(self.confirm_url, data="invalid JSON", content_type="application/json")
            self.assertEqual(response.status_code, 400)

            response_data = json.loads(response.content)
            self.assertIn("error", response_data)
            self.assertEqual(response_data.get("error"), "Invalid JSON")

        def test_invalid_data_format_confirmation_list_is_no_list(self):
            request_data = {
                "confirmationList": {}
            }

            response = self.client.put(self.confirm_url, json.dumps(request_data), content_type="application/json")
            self.assertEqual(response.status_code, 400)

            response_data = json.loads(response.content)
            self.assertIn("error", response_data)
            self.assertEqual(response_data.get("error"), "Invalid data format: 'confirmationList' should be a list")

        def test_invalid_data_format_no_dicts_in_confirmation_list(self):
            request_data = {
                "confirmationList": [
                    [self.test_student.id, [self.class_one.id, self.class_two.id]],
                ]
            }

            response = self.client.put(self.confirm_url, json.dumps(request_data), content_type="application/json")
            self.assertEqual(response.status_code, 400)

            response_data = json.loads(response.content)
            self.assertIn("error", response_data)
            self.assertEqual(response_data.get("error"), "Invalid data format: Each item in 'confirmationList' should be a dictionary")

class AttendanceTestCase(TestCase):
    pass

class PaymentTestCase(TestCase):
    def positive_response_helper(self, response, expected_status, message):
        self.assertEqual(response.status_code, expected_status)
        response_data = json.loads(response.content)
        self.assertIn("message", response_data)
        self.assertEqual(response_data.get("message"), message)

    def base_positive_response_content_helper(self, response_data):
        self.assertIn("paymentId", response_data)

        self.assertIn("studentId", response_data)
        self.assertEqual(response_data.get("studentId"), self.test_student.id)

        self.assertIn("classId", response_data)
        self.assertEqual(response_data.get("studentId"), self.class_one.id)

        self.assertIn("amount", response_data)
        self.assertTrue(isinstance, response_data.get("amount"))

        self.assertIn("paymentMonth", response_data)
        self.assertIn("paymentYear", response_data)

    def additional_positive_response_content_helper(self, response_data):
        self.assertIn("studentName", response_data)
        student_name = f"{self.test_student.first_name} {self.test_student.last_name}"
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
        response_data = json.loads(response.content)
        return response_data

    def base_positive_validation(self, request_data):
        response = self.client.post(self.payments_url, json.dumps(request_data), content_type="application/json")
        self.positive_response_helper(response, 200, "Payment was successfully created")

        response_data = self.get_response_data_helper(response)
        self.base_positive_response_content_helper(response_data)
        self.additional_positive_response_content_helper(response_data)

        payment_record_id = Payment.objects.get(id=response_data.get("paymentId"))
        self.assertEqual(payment_record_id.id, response_data.get("paymentId"))

    def base_negative_validation_invalid_request_fields(self, request_data, status_code, error_message):
        response = self.client.post(self.payments_url, json.dumps(request_data), content_type="application/json")
        self.assertEqual(response.status_code, status_code)

        response_data = self.get_response_data_helper(response)
        self.assertIn("error", response_data)
        self.assertEqual(response_data.get("error"), error_message)

    def setUp(self):
        self.test_student = Student.objects.create(first_name="John", last_name="Testovich")
        self.class_one = ClassModel.objects.create(name="Foil")

        # Django may internally convert isoformat string back into a naive datetime if it's missing timezone info
        # To be safe, it's better to store the actual aware datetime object, not the string
        self.today = now() # have an object, not str, with timezone included, convert to string later
        self.today_naive = datetime.now() # have a naive object, without timezone included, convert to string later

        self.payments_url = reverse("payments")

    # TODO: add tests for month and year

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

        self.base_negative_validation_invalid_request_fields(request_data, 400, "Missing required fields")

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

        self.base_negative_validation_invalid_request_fields(request_data, 400, "Missing required fields")

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

        self.base_negative_validation_invalid_request_fields(request_data, 400, "Invalid datetime format for payment date")

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

        self.base_negative_validation_invalid_request_fields(request_data, 400, "Missing required fields")

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

        self.base_negative_validation_invalid_request_fields(request_data, 400, "Invalid date format for month or year")

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

        self.base_negative_validation_invalid_request_fields(request_data, 400, "Invalid value for month: should be between 1 and 12")

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
        payment_record_for_another_month = Payment.objects.filter(payment_month=another_payment_month)
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
        payment_record_for_another_month = Payment.objects.filter(payment_year=another_payment_year)
        self.assertEqual(payment_record_for_another_month.count(), 1)

class ClassesTestCase(TestCase):
    def setUp(self):
        self.classes_url = reverse("classes")
        self.class_one_name = "Test Class One"

    def positive_response_helper(self, response, expected_status, message):
        self.assertEqual(response.status_code, expected_status)
        response_data = json.loads(response.content)
        self.assertIn("message", response_data)
        self.assertEqual(response_data.get("message"), message)

    def positive_response_content_helper(self, response, expected_class_name=""):
        response_data = json.loads(response.content)
        self.assertIn("id", response_data)
        self.assertIn("name", response_data)

        if expected_class_name:
            self.assertEqual(response_data["name"], expected_class_name)

    def error_response_helper(self, response, expected_code, expected_message):
        self.assertEqual(response.status_code, expected_code)
        response_data = json.loads(response.content)
        self.assertIn("error", response_data)
        self.assertEqual(response_data.get("error"), expected_message)


    def test_create_class_successfully(self):
        request_data = {
            "name": self.class_one_name
        }

        response = self.client.post(self.classes_url, json.dumps(request_data), content_type="application/json")
        self.positive_response_helper(response, 200, "Class was created successfully")
        self.positive_response_content_helper(response=response, expected_class_name=self.class_one_name)

    def test_class_with_empty_name_not_created(self):
        request_data = {
            "name": ""
        }

        response = self.client.post(self.classes_url, json.dumps(request_data), content_type="application/json")
        self.error_response_helper(response, 400, "Class name should not be empty")


class StudentsTestCase(TestCase):
    def setUp(self):
        self.students_url = reverse("students")
        self.first_name_one = "First"
        self.last_name_one = "Last"

    def positive_response_helper(self, response, expected_status, message):
        self.assertEqual(response.status_code, expected_status)
        response_data = json.loads(response.content)
        self.assertIn("message", response_data)
        self.assertEqual(response_data.get("message"), message)

    def positive_response_content_helper(self, response, expected_first_name, expected_last_name):
        response_data = json.loads(response.content)
        self.assertIn("studentId", response_data)
        self.assertIn("firstName", response_data)
        self.assertIn("lastName", response_data)

        self.assertEqual(response_data["firstName"], expected_first_name)
        self.assertEqual(response_data["lastName"], expected_last_name)

    def error_response_helper(self, response, expected_code, expected_message):
        self.assertEqual(response.status_code, expected_code)
        response_data = json.loads(response.content)
        self.assertIn("error", response_data)
        self.assertEqual(response_data.get("error"), expected_message)


    def test_create_student_successfully(self):
        request_data = {
            "firstName": self.first_name_one,
            "lastName": self.last_name_one,
        }

        response = self.client.post(self.students_url, json.dumps(request_data), content_type="application/json")
        self.positive_response_helper(response, 200, "Student was created successfully")
        self.positive_response_content_helper(
            response=response,
            expected_first_name=self.first_name_one,
            expected_last_name=self.last_name_one)

    def test_student_with_empty_both_first_last_names_not_created(self):
        request_data = {
            "firstName": "",
            "lastName": "",
        }

        response = self.client.post(self.students_url, json.dumps(request_data), content_type="application/json")
        self.error_response_helper(response, 400, "First and last name should not be empty")

    def test_student_with_empty_first_name_not_created(self):
        request_data = {
            "firstName": "",
            "lastName": self.last_name_one,
        }

        response = self.client.post(self.students_url, json.dumps(request_data), content_type="application/json")
        self.error_response_helper(response, 400, "First and last name should not be empty")


class SchedulesTestCase(TestCase):
    def setUp(self):
        self.schedules_url = reverse("schedules")
        self.class_one = ClassModel.objects.create(name="Foil")
        self.class_two = ClassModel.objects.create(name="Heavy sabre")
        self.day_one = Day.objects.create(name="Monday")
        self.day_two = Day.objects.create(name="Tuesday")
        self.time_one = "10:00:00"
        self.time_two = "15:30:00"

    def positive_response_helper(self, response, expected_status, message):
        self.assertEqual(response.status_code, expected_status)
        response_data = json.loads(response.content)
        self.assertIn("message", response_data)
        self.assertEqual(response_data.get("message"), message)

    def positive_response_content_helper(self,
                                         response,
                                         expected_class_id,
                                         expected_class_name,
                                         expected_day,
                                         expected_time):
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
        self.assertEqual(response.status_code, expected_code)
        response_data = json.loads(response.content)
        self.assertIn("error", response_data)
        self.assertEqual(response_data.get("error"), expected_message)

    def test_schedule_class_successfully(self):
        request_data = {
            "classId": self.class_one.id,
            "day": self.day_one.name,
            "classTime": self.time_one,
        }

        response = self.client.post(self.schedules_url, json.dumps(request_data), content_type="application/json")
        self.positive_response_helper(response, 200, "Schedule was created successfully")
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
        }

        response = self.client.post(self.schedules_url, json.dumps(request_data), content_type="application/json")
        self.error_response_helper(response, 400, "Missing required fields")

    def test_class_with_incorrect_class_id_not_scheduled(self):
        request_data = {
            "classId": 12354,
            "day": self.day_one.name,
            "classTime": self.time_one,
        }

        response = self.client.post(self.schedules_url, json.dumps(request_data), content_type="application/json")
        self.error_response_helper(response, 404, "Class not found")

    def test_class_with_incorrect_day_name_not_scheduled(self):
        request_data = {
            "classId": self.class_one.id,
            "day": "Mon",
            "classTime": self.time_one,
        }

        response = self.client.post(self.schedules_url, json.dumps(request_data), content_type="application/json")
        self.error_response_helper(response, 404, "Day not found")

    def test_class_with_incorrect_time_format_not_scheduled(self):
        request_data = {
            "classId": self.class_one.id,
            "day": self.day_one.name,
            "classTime": "3PM",
        }

        response = self.client.post(self.schedules_url, json.dumps(request_data), content_type="application/json")
        self.error_response_helper(response, 400, "Invalid time format")

    def test_can_not_schedule_two_classes_at_the_same_day_and_time(self):
        request_data_one = {
            "classId": self.class_one.id,
            "day": self.day_one.name,
            "classTime": self.time_one,
        }

        request_data_two = {
            "classId": self.class_two.id,
            "day": self.day_one.name,
            "classTime": self.time_one,
        }

        response = self.client.post(self.schedules_url, json.dumps(request_data_one), content_type="application/json")
        self.positive_response_helper(response, 200, "Schedule was created successfully")
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
                    class_time=time(10, 0, 0)
                )

    # TODO: add view test for attempt to schedule two classes to the same time

class TimeSlotsTestCase(TestCase):
    def setUp(self):
        self.slots_url = reverse("available_time_slots")
        self.class_one = ClassModel.objects.create(name="Foil", duration_minutes=60)
        self.class_two = ClassModel.objects.create(name="Heavy sabre", duration_minutes=90)
        self.day_one_name = "Monday"
        self.day_two_name = "Tuesday"
        self.day_one = Day.objects.create(name=self.day_one_name)
        self.day_two = Day.objects.create(name=self.day_two_name)
        self.time_one = "10:00:00"
        self.time_two = "15:30:00"
        self.schedule_one = Schedule.objects.create(class_model=self.class_one, day=self.day_two, class_time=parse_time(self.time_one))
        self.schedule_two = Schedule.objects.create(class_model=self.class_two, day=self.day_two, class_time=parse_time(self.time_two))

        self.new_class_duration = 60

        self.available_slots_day_one = ["08:00", "08:30", "09:00", "09:30",
                                        "10:00", "10:30", "11:00", "11:30",
                                        "12:00", "12:30", "13:00", "13:30",
                                        "14:00", "14:30", "15:00", "15:30",
                                        "16:00", "16:30", "17:00", "17:30",
                                        "18:00", "18:30", "19:00", "19:30",
                                        "20:00"]
        self.available_slots_day_two = ["08:00", "08:30", "09:00", "11:00",
                                        "11:30", "12:00", "12:30", "13:00",
                                        "13:30", "14:00", "14:30", "17:00",
                                        "17:30", "18:00", "18:30","19:00",
                                        "19:30", "20:00"]

    def positive_response_helper(self, response, expected_status, message):
        self.assertEqual(response.status_code, expected_status)
        response_data = json.loads(response.content)
        self.assertIn("message", response_data)
        self.assertEqual(response_data.get("message"), message)

    def positive_response_content_helper(self,
                                         response,
                                         expected_available_slots):
        response_data = json.loads(response.content)
        self.assertIn("availableSlots", response_data)

        returned_slots = response_data.get("availableSlots") if response_data.get("availableSlots") else []
        self.assertEqual(len(returned_slots), len(expected_available_slots))

        return returned_slots

    def error_response_helper(self, response, expected_code, expected_message):
        self.assertEqual(response.status_code, expected_code)
        response_data = json.loads(response.content)
        self.assertIn("error", response_data)
        self.assertEqual(response_data.get("error"), expected_message)

    def test_empty_day_has_all_available_intervals(self):
        response = self.client.get(self.slots_url, {"day": self.day_one_name, "duration": self.new_class_duration})
        self.positive_response_helper(response, 200, "Available time slots")
        returned_slots = self.positive_response_content_helper(response, self.available_slots_day_one)

        for slot in self.available_slots_day_one:
            self.assertIn(slot, returned_slots)

    def test_busy_day_only_available_intervals(self):
        response = self.client.get(self.slots_url, {"day": self.day_two_name, "duration": self.new_class_duration})
        self.positive_response_helper(response, 200, "Available time slots")
        returned_slots = self.positive_response_content_helper(response, self.available_slots_day_two)
        print(returned_slots)

        for slot in self.available_slots_day_two:
                self.assertIn(slot, returned_slots)

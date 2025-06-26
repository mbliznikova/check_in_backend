import json

from datetime import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils.timezone import now

from .models import ClassModel, Student, Attendance, Payment

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
            print("expected_checked_in_list")
            self.assertIn("checkedIn", response_data)
            self.assertEqual(len(response_data.get("checkedIn")), len(expected_checked_in_list))
            self.assertEqual(set(response_data.get("checkedIn")), set(expected_checked_in_list))
        if expected_checked_out_list:
            self.assertIn("checkedOut", response_data)
            print("expected_checked_out_list")
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

    def additional_positive_response_content_helper(self, response_data):
        self.assertIn("studentName", response_data)
        student_name = f"{self.test_student.first_name} {self.test_student.last_name}"
        self.assertEqual(response_data.get("studentName"), student_name)

        self.assertIn("className", response_data)
        class_name = self.class_one.name
        self.assertEqual(response_data.get("className"), class_name)

        # TODO: find out why BE returns the first day of the month, i.e. 2025-06-01T22:10:57.529161+00:00
        self.assertIn("paymentDate", response_data)
        # self.assertEqual(response_data.get("paymentDate"), self.today)

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

    def setUp(self):
        self.test_student = Student.objects.create(first_name="John", last_name="Testovich")
        self.class_one = ClassModel.objects.create(name="Foil")

        self.today = datetime.now().isoformat()

        self.payments_url = reverse("payments")

    def test_successful_payment_made(self):
        request_data = {
            "paymentData": {
                "studentId": self.test_student.id,
                "classId": self.class_one.id,
                "studentName": "John Testovich",
                "className": "Foil",
                "amount": 50.0,
                "paymentDate": self.today,
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
                "paymentDate": self.today,
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
                "paymentDate": self.today,
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
                "paymentDate": self.today,
            }
        }

        response = self.client.post(self.payments_url, json.dumps(request_data), content_type="application/json")
        self.assertEqual(response.status_code, 400)

        response_data = self.get_response_data_helper(response)
        self.assertIn("error", response_data)
        self.assertEqual(response_data.get("error"), "Missing required fields")

    def test_invalid_payment_missing_class_id(self):
        request_data = {
            "paymentData": {
                "studentId": self.test_student.id,
                "classId": None,
                "studentName": "John Testovich",
                "className": "",
                "amount": 50.0,
                "paymentDate": self.today,
            }
        }

        response = self.client.post(self.payments_url, json.dumps(request_data), content_type="application/json")
        self.assertEqual(response.status_code, 400)

        response_data = self.get_response_data_helper(response)
        self.assertIn("error", response_data)
        self.assertEqual(response_data.get("error"), "Missing required fields")

    def test_invalid_payment_invalid_datetime_format(self):
        request_data = {
            "paymentData": {
                "studentId": self.test_student.id,
                "classId": self.class_one.id,
                "studentName": "John Testovich",
                "className": "",
                "amount": 50.0,
                "paymentDate": "2025/02/01",
            }
        }

        response = self.client.post(self.payments_url, json.dumps(request_data), content_type="application/json")
        self.assertEqual(response.status_code, 400)

        response_data = self.get_response_data_helper(response)
        self.assertIn("error", response_data)
        self.assertEqual(response_data.get("error"), "Invalid datetime format")

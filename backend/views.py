import json

from datetime import datetime

from django.db.models import Sum
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now, is_naive, make_aware
from django.utils.dateparse import parse_datetime

from .models import ClassModel, Student, Day, Schedule, Attendance, Price, Payment
from .serializers import CaseSerializer, StudentSerializer, ClassModelSerializer, AttendanceSerializer, PaymentSerializer, MonthlyPaymentsSummary, ScheduleSerializer

def make_error_json_response(error_message, status_code):
    return JsonResponse({"error": error_message}, status=status_code)

def make_success_json_response(status_code, message="Success", response_body=None):
    if response_body:
        return JsonResponse(response_body, status=status_code)
    return JsonResponse({"message": message}, status=status_code)

def classes_list(request):
    today_name = datetime.today().strftime("%A")

    today_day_object = Day.objects.filter(name=today_name).first()
    # TODO: handle the case when there is no such objects? Empty list in response?
    # Assume (for now) that it always be, because the table should be pre-populated with all weekdays?

    scheduled_today = Schedule.objects.filter(day=today_day_object).values("class_model")

    classes = ClassModel.objects.filter(id__in=scheduled_today)
    # Should they be sorted? If yes, how? Alphabetical or based on scheduled time?

    serializer = ClassModelSerializer(classes, many=True)

    response = {
        "response": serializer.data
    }

    return JsonResponse(response)

@csrf_exempt
@require_http_methods(["POST"])
def classes(request):
    try:
        request_body = json.loads(request.body)
        name = request_body.get("name", "")

        if not name:
            return make_error_json_response("Class name should not be empty", 400)

        data_to_write = {
            "name": name
        }

        serializer = ClassModelSerializer(data=data_to_write)
        if serializer.is_valid():
            saved_class = serializer.save()
        else:
            return make_error_json_response(serializer.errors, 400)

        response = ClassModelSerializer.dict_to_camel_case( # for the case there will be camel case in the future
            {
                "message": "Class was created successfully",
                "id": saved_class.id,
                "name": saved_class.name,
            }
        )

        return make_success_json_response(200, response_body=response)

    except json.JSONDecodeError:
        return make_error_json_response("Invalid JSON", 400)
    except Exception as e:
        return make_error_json_response(f"An unexpected error occurred: {e}", 500)

@csrf_exempt
@require_http_methods(["GET", "POST"])
def schedules(request):
    if request.method == "GET":
        schedules = Schedule.objects.all()
        serializer = ScheduleSerializer(schedules, many=True)

        response = {
            "response": serializer.data
        }

        return JsonResponse(response)

    if request.method == "POST":
        try:
            request_body = json.loads(request.body)
            # TODO: handle request body parsing

        except json.JSONDecodeError:
            return make_error_json_response("Invalid JSON", 400)
        except Exception as e:
            return make_error_json_response(f"An unexpected error occurred: {e}", 500)

@csrf_exempt
@require_http_methods(["GET", "POST"])
def students(request):
    if request.method == "GET":
        students = Student.objects.all()
        serializer = StudentSerializer(students, many=True)

        response = {
            "response": serializer.data
        }

        return JsonResponse(response)

    if request.method == "POST":
        try:
            request_body = json.loads(request.body)
            first_name = request_body.get("firstName", "")
            last_name = request_body.get("lastName", "")

            if not first_name or not last_name:
                return make_error_json_response("First and last name should not be empty", 400)

            data_to_write = {
                "first_name": first_name,
                "last_name": last_name,
            }

            serializer = StudentSerializer(data=data_to_write)
            if serializer.is_valid():
                saved_student = serializer.save()

            respone = StudentSerializer.dict_to_camel_case(
                {
                    "message": "Student was created successfully",
                    "student_id": saved_student.id,
                    "first_name": saved_student.first_name,
                    "last_name": saved_student.last_name,
                }
            )

            return make_success_json_response(200, response_body=respone)

        except json.JSONDecodeError:
            return make_error_json_response("Invalid JSON", 400)
        except Exception as e:
            return make_error_json_response(f"An unexpected error occurred: {e}", 500)

@csrf_exempt
@require_http_methods(["POST"])
def check_in(request):
    # For now this view sreves for insertion and deletion entries to/from Attendance table since the data with classes
    # a student attends to arrives complete every time, like a source of truth
    try:
        request_body = json.loads(request.body)
        # Check if body?
        check_in_data = request_body.get("checkInData", {})
        student_id = check_in_data.get("studentId")
        classes_list = check_in_data.get("classesList", [])
        today_date = check_in_data.get("todayDate")

        if not student_id or not today_date:
            return make_error_json_response("Missing required fields", 400)

        # TODO: add parsing for today_date
        existing_classes = set(Attendance.objects.filter(student_id=student_id, attendance_date=today_date).values_list("class_id", flat=True))
        classes_to_add = set(classes_list) - existing_classes
        classes_to_delete = existing_classes - set(classes_list)

        classes_to_add_response, classes_to_delete_response = [], []

        # Can rewrite to use Attendance.objects.create() instead of using serializer, but then have to retrieve
        # instance of Student by student_id and pass as a FK
        for cls in classes_to_add:
            data_to_write = {
                    "student_id": student_id,
                    "class_id": cls,
                    "attendance_date": today_date,
                }
            serializer = AttendanceSerializer(data=data_to_write)
            if serializer.is_valid():
                serializer.save()
                classes_to_add_response.append(cls)
            else:
                return make_error_json_response(serializer.errors, 400)

        if classes_to_delete:
            Attendance.objects.filter(student_id=student_id, attendance_date=today_date, class_id__in=classes_to_delete).delete()

            for cls in classes_to_delete:
                classes_to_delete_response.append(cls)

        response = CaseSerializer.dict_to_camel_case(
            {
                "message": "Check-in data was successfully updated",
                "student_id": student_id,
                "attendance_date": today_date,
                "checked_in": classes_to_add_response,
                "checked_out": classes_to_delete_response,
            })

        return make_success_json_response(200, response_body=response)

    except json.JSONDecodeError:
        return make_error_json_response("Invalid JSON", 400)
    except Exception as e:
        return make_error_json_response(f"An unexpected error occurred: {e}", 500)

def get_attended_students(request):
    attended_today = Attendance.objects.filter(attendance_date=now().date())
    student_class_ids = attended_today.values_list("student_id", "class_id")

    student_classes = {}

    for student_id, class_id in student_class_ids:
        student_classes.setdefault(student_id, []).append(class_id)

    students_attended_today = Student.objects.filter(id__in=student_classes.keys())

    response = CaseSerializer.dict_to_camel_case(
        {
            "confirmed_attendance":
            [
                CaseSerializer.dict_to_camel_case({
                    "id": student.id,
                    "first_name": student.first_name,
                    "last_name": student.last_name,
                    "classes": student_classes.get(student.id, []),
                })
                for student in students_attended_today
            ]
        })

    return make_success_json_response(200, response_body=response)

@csrf_exempt
@require_http_methods(["PUT"])
def confirm(request):
    try:
        request_body = json.loads(request.body)

        confirmation_list = request_body.get("confirmationList", [])
        # TODO: what would be the default today_date value?
        confirmation_day = request_body.get("date", now().date())

        attended_today = Attendance.objects.filter(attendance_date=confirmation_day)

        if not isinstance(confirmation_list, list):
            return make_error_json_response("Invalid data format: 'confirmationList' should be a list", 400)

        confirmed_attendance = {}
        for confirmation in confirmation_list:
            if not isinstance(confirmation, dict):
                return make_error_json_response("Invalid data format: Each item in 'confirmationList' should be a dictionary", 400)
            confirmed_attendance.update(confirmation)

        confirmed_attendance = {
            int(student_id_key): {
                    int(class_id_key): bool(value) for class_id_key, value in classes.items()
                }
                for student_id_key, classes in confirmed_attendance.items()
            }

        attendance_to_delete, attendance_to_update = [], []

        for attendance in attended_today:
            student_id = attendance.student_id.id
            class_id = attendance.class_id.id

            if student_id not in confirmed_attendance or class_id not in confirmed_attendance[student_id]:
                attendance_to_delete.append(attendance.id)
                continue

            new_is_showed_up_value = confirmed_attendance.get(student_id, {}).get(class_id)

            if attendance.is_showed_up != new_is_showed_up_value:
                attendance.is_showed_up = new_is_showed_up_value
                attendance_to_update.append(attendance)

        if attendance_to_delete:
            Attendance.objects.filter(id__in=attendance_to_delete).delete()

        if attendance_to_update:
            Attendance.objects.bulk_update(attendance_to_update, ["is_showed_up"])

        response = {
            "message": "Attendance confirmed successfully"
        }

        return make_success_json_response(200, response_body=response)

    except json.JSONDecodeError:
        return make_error_json_response("Invalid JSON", 400)
    except Exception as e:
        return make_error_json_response(f"An unexpected error occurred: {e}", 500)

def attendance_list(request):
    request_month = request.GET.get("month")
    request_year = request.GET.get("year")

    attendances = None

    if request_month and request_year:
        try:
            request_month = int(request_month)
            request_year = int(request_year)

            # TODO: add tests

            if not (1 <= request_month <= 12):
                return make_error_json_response(f"Month must be between 1 and 12, not {request_month}", 400)

            # TODO: think about acceptable year range
            if not (2000 <= request_year <= now().year + 1):
                return make_error_json_response(f"Invalid year: {request_year}", 400)

            attendances = Attendance.objects.all().order_by("-attendance_date").filter(
                attendance_date__month=request_month,
                attendance_date__year=request_year
            )
        except ValueError:
            return make_error_json_response("Invalid month or year", 400)
    else:
        attendances = Attendance.objects.all().order_by("-attendance_date")

    attendance_dict = {}

    for att in attendances:
        str_date = att.attendance_date.isoformat()
        str_class_id = str(att.class_id.id)
        str_class_name = str(att.class_id.name)
        str_student_id = str(att.student_id.id)
        str_student_first_name = str(att.student_id.first_name)
        str_student_last_name = str(att.student_id.last_name)

        if str_date not in attendance_dict:
            attendance_dict[str_date] = {}

        if str_class_id not in attendance_dict[str_date]:
           attendance_dict[str_date][str_class_id] = {
               "name": str_class_name,
               "students": {}
           }

        attendance_dict[str_date][str_class_id]["students"][str_student_id] = CaseSerializer.dict_to_camel_case({
            "first_name": str_student_first_name,
            "last_name": str_student_last_name,
            "is_showed_up": att.is_showed_up
        })

    # TODO: Write tests

    result_list = []
    for date, class_data in attendance_dict.items():
        result_list.append(
            CaseSerializer.dict_to_camel_case({
                "date": date,
                "classes": class_data,
            })
        )

    response = {
        "response": result_list
    }

    return make_success_json_response(200, response_body=response)

def prices_list(request):
    prices = Price.objects.all()

    price_dict = {}
    for price in prices:
        price_dict[str(price.class_id.id)] = {price.class_id.name: price.amount}

    response = {
        "response": price_dict
    }

    return make_success_json_response(200, response_body=response)

@csrf_exempt
@require_http_methods(["GET", "POST"])
def payments(request):
    if request.method == "GET":
        payment_month_param = request.GET.get('month', now().month)
        payment_year_param = request.GET.get('year', now().year)
        payments = Payment.objects.all().filter(
            payment_month = payment_month_param,
            payment_year = payment_year_param)
        serializer = PaymentSerializer(payments, many=True)

        response = {
            "response": serializer.data
        }

        return make_success_json_response(200, response_body=response)

    if request.method == "POST":
        try:
            request_body = json.loads(request.body)
            payment_data = request_body.get("paymentData", {})
            student_id = payment_data.get("studentId")
            class_id = payment_data.get("classId")
            student_name = payment_data.get("studentName")
            class_name = payment_data.get("className")
            amount = payment_data.get("amount")
            payment_date_str = payment_data.get("paymentDate")
            month = payment_data.get("month")
            year = payment_data.get("year")

            if not student_id or not class_id or not amount:
                return make_error_json_response("Missing required fields", 400)

            if not month or not year:
                return make_error_json_response("Missing required fields", 400)

            if not student_name:
                try:
                    student = Student.objects.get(id=student_id)
                    student_name = f"{student.first_name} {student.last_name}"
                except Student.DoesNotExist:
                    return make_error_json_response("Student not found", 404)

            if not class_name:
                try:
                    cls = ClassModel.objects.get(id=class_id)
                    class_name = f"{cls.name}"
                except Student.DoesNotExist:
                    return make_error_json_response("Class not found", 404)

            payment_date = parse_datetime(payment_date_str) if payment_date_str else None

            if payment_date is None and payment_date_str:
                return make_error_json_response("Invalid datetime format for payment date", 400)

            if not isinstance(month, int) or not isinstance(year, int):
                return make_error_json_response("Invalid date format for month or year", 400)

            if not (1 <= month <= 12):
                return make_error_json_response("Invalid value for month: should be between 1 and 12", 400)

            # TODO: the way to validate the value of the year: how far backward/forward?

            # TODO: handle time zones?
            if payment_date and is_naive(payment_date):
                payment_date = make_aware(payment_date)

            data_to_write = {
                "student_id": student_id,
                "class_id": class_id,
                "student_name": student_name,
                "class_name": class_name,
                "amount": amount,
                "payment_month": month,
                "payment_year": year,
            }

            if payment_date:
                data_to_write["payment_date"] = payment_date

            serializer = PaymentSerializer(data=data_to_write)

            if serializer.is_valid():
                saved_payment = serializer.save()
            else:
                return make_error_json_response(serializer.errors, 400)

            response = PaymentSerializer.dict_to_camel_case(
                {
                    "message": "Payment was successfully created",
                    "payment_id": saved_payment.id,
                    "student_id": saved_payment.student_id.id if saved_payment.student_id else None,
                    "class_id": saved_payment.class_id.id if saved_payment.class_id else None,
                    "student_name": saved_payment.student_name,
                    "class_name": saved_payment.class_name,
                    "amount": saved_payment.amount,
                    "payment_date": saved_payment.payment_date.isoformat(),
                    "payment_month": saved_payment.payment_month,
                    "payment_year": saved_payment.payment_year,
                }
            )

            return make_success_json_response(200, response_body=response)

        except json.JSONDecodeError:
            return make_error_json_response("Invalid JSON", 400)

def payment_summary(request):
    # By default returns for the current month (for now)
    # Should I calculate it from payments? Every time or by a separate request only?
    # If there is an existing entry - compare and recalculate if needed

    payment_summary = Payment.objects.filter(
        payment_year = now().year,
        payment_month = now().month
    )

    new_summary = payment_summary.aggregate(Sum("amount"))["amount__sum"] or 0.0

    # TODO: handle logic to add new entry for MonthlyPaymentsSummary or update the existing one
    # if new_summary != old_summary or not old_summary:
    old_summary = MonthlyPaymentsSummary.objects.filter(
        summary_date__year = now().year,
        summary_date__month = now().month
    )

    summary = {"summary": new_summary}

    response = {
        "response": summary
    }

    return make_success_json_response(200, response_body=response)

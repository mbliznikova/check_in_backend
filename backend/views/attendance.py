import json

from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from backend.decorators import kiosk_or_above, teacher_or_above
from backend.models import Attendance, Student
from backend.serializers import (
    AttendanceSerializer, CaseSerializer,
)
from backend.views.helpers import (
    make_error_json_response, make_success_json_response,
)


@csrf_exempt
@kiosk_or_above
@require_http_methods(["POST"])
def check_in(request):
    try:
        request_body = json.loads(request.body)
        check_in_data = request_body.get("checkInData", {})
        student_id = check_in_data.get("studentId")
        class_occurrences_list = check_in_data.get("classOccurrencesList", [])
        today_date = check_in_data.get("todayDate")

        if not student_id or not today_date:
            return make_error_json_response("Missing required fields", 400)

        existing_occurrences = set(
            Attendance.objects.filter(
                student_id=student_id,
                attendance_date=today_date,
                school=request.school,
            ).values_list("class_occurrence", flat=True)
        )
        to_add = set(class_occurrences_list) - existing_occurrences
        to_delete = existing_occurrences - set(class_occurrences_list)

        to_add_response, to_delete_response = [], []

        for occ in to_add:
            data_to_write = {
                "student_id": student_id,
                "class_occurrence": occ,
                "attendance_date": today_date,
            }

            serializer = AttendanceSerializer(data=data_to_write)

            if serializer.is_valid():
                serializer.save(school=request.school)
                to_add_response.append(occ)
            else:
                return make_error_json_response(serializer.errors, 400)

        if to_delete:
            Attendance.objects.filter(
                student_id=student_id,
                attendance_date=today_date,
                class_occurrence__in=to_delete,
                school=request.school,
            ).delete()

            for occ in to_delete:
                to_delete_response.append(occ)

        response = CaseSerializer.dict_to_camel_case({
            "message": "Check-in data was successfully updated",
            "student_id": student_id,
            "attendance_date": today_date,
            "checked_in": to_add_response,
            "checked_out": to_delete_response,
        })

        return make_success_json_response(200, response_body=response)

    except json.JSONDecodeError:
        return make_error_json_response("Invalid JSON", 400)
    except Exception:
        return make_error_json_response("An internal error occurred", 500)


@kiosk_or_above
def get_attended_students(request):
    attended_today = Attendance.objects.filter(
        attendance_date=now().date(),
        school=request.school,
    )
    student_occurrence_ids = attended_today.values_list(
        "student_id", "class_occurrence", "class_name")

    student_occurrence = {}

    for student_id, occurrence_id, class_name in student_occurrence_ids:
        student_occurrence.setdefault(student_id, []).append(
            [occurrence_id, class_name])

    students_attended_today_occ = Student.objects.filter(
        id__in=student_occurrence.keys(),
        school=request.school,
    )

    response = CaseSerializer.dict_to_camel_case({
        "confirmed_attendance": [
            CaseSerializer.dict_to_camel_case({
                "id": student.id,
                "first_name": student.first_name,
                "last_name": student.last_name,
                "classes": [occ[-1] for occ in student_occurrence.get(student.id, [])],
                "occurrences": [occ[0] for occ in student_occurrence.get(student.id, [])],
            })
            for student in students_attended_today_occ
        ]
    })

    return make_success_json_response(200, response_body=response)


@teacher_or_above
@csrf_exempt
@require_http_methods(["PUT"])
def confirm(request):
    try:
        request_body = json.loads(request.body)

        confirmation_list = request_body.get("confirmationList", [])
        confirmation_day = request_body.get("date", now().date())

        attended_today = Attendance.objects.filter(
            attendance_date=confirmation_day,
            school=request.school,
        )

        if not isinstance(confirmation_list, list):
            return make_error_json_response(
                "Invalid data format: 'confirmationList' should be a list", 400)

        confirmed_attendance = {}

        for confirmation in confirmation_list:
            if not isinstance(confirmation, dict):
                return make_error_json_response(
                    "Invalid data format: Each item in 'confirmationList' should be a dictionary", 400)
            confirmed_attendance.update(confirmation)

        confirmed_attendance = {
            int(student_id_key): {
                int(occurrence_id_key): bool(value) for occurrence_id_key,
                value in occurrences.items()} for student_id_key,
            occurrences in confirmed_attendance.items()}

        to_delete, to_update = [], []

        for attendance in attended_today:
            student_id = attendance.safe_student_id
            occurrence_id = attendance.safe_occurrence_id

            if student_id not in confirmed_attendance or occurrence_id not in confirmed_attendance[
                    student_id]:
                to_delete.append(attendance.id)
                continue

            new_is_showed_up_value = confirmed_attendance.get(
                student_id, {}).get(occurrence_id)

            if attendance.is_showed_up != new_is_showed_up_value:
                attendance.is_showed_up = new_is_showed_up_value
                to_update.append(attendance)

        if to_delete:
            Attendance.objects.filter(
                id__in=to_delete,
                school=request.school,
            ).delete()

        if to_update:
            Attendance.objects.bulk_update(to_update, ["is_showed_up"])

        response = {
            "message": "Attendance confirmed successfully"
        }

        return make_success_json_response(200, response_body=response)

    except json.JSONDecodeError:
        return make_error_json_response("Invalid JSON", 400)
    except Exception:
        return make_error_json_response("An internal error occurred", 500)


@teacher_or_above
@require_http_methods(["GET"])
def attendance_list(request):
    request_month = request.GET.get("month")
    request_year = request.GET.get("year")

    attendances = None

    if request_month and request_year:
        try:
            request_month = int(request_month)
            request_year = int(request_year)

            if not (1 <= request_month <= 12):
                return make_error_json_response(
                    f"Month must be between 1 and 12, not {request_month}", 400)

            if not (2000 <= request_year <= now().year + 1):
                return make_error_json_response(
                    f"Invalid year: {request_year}", 400)

            attendances = Attendance.objects.filter(
                school=request.school,
            ).order_by("-attendance_date").filter(
                attendance_date__month=request_month,
                attendance_date__year=request_year
            )
        except ValueError:
            return make_error_json_response("Invalid month or year", 400)
    else:
        attendances = Attendance.objects.filter(
            school=request.school,
        ).order_by("-attendance_date")

    attendance_dict = {}

    for att in attendances:
        str_date = att.attendance_date.isoformat()
        str_class_id = str(att.safe_class_id or "")
        str_class_name = att.safe_class_name or ""
        str_student_id = str(att.safe_student_id or "")
        str_student_first_name = att.student_first_name or ""
        str_student_last_name = att.student_last_name or ""
        str_occurrence_id = str(att.safe_occurrence_id or "")
        str_actual_time = str(
            att.class_occurrence.actual_start_time if att.class_occurrence else "")

        if str_date not in attendance_dict:
            attendance_dict[str_date] = {}

        if str_occurrence_id not in attendance_dict[str_date]:
            attendance_dict[str_date][str_occurrence_id] = (
                CaseSerializer.dict_to_camel_case({
                    "name": str_class_name,
                    "time": str_actual_time,
                    "class_id": str_class_id,
                    "students": {},
                })
            )

        attendance_dict[str_date][str_occurrence_id]["students"][str_student_id] = (
            CaseSerializer.dict_to_camel_case({
                "first_name": str_student_first_name,
                "last_name": str_student_last_name,
                "is_showed_up": att.is_showed_up
            })
        )

    result_list_new = []
    for date, class_data in attendance_dict.items():
        result_list_new.append({
            "date": date,
            "occurrences": class_data,
        })

    response = {
        "response": result_list_new
    }

    return make_success_json_response(200, response_body=response)

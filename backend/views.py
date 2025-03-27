import json

from datetime import datetime

from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now

from .models import ClassModel, Student, Day, Schedule, Attendance
from .serializers import CaseSerializer, StudentSerializer, ClassModelSerializer, AttendanceSerializer

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

def student_list(request):
    students = Student.objects.all()
    serializer = StudentSerializer(students, many=True)

    response = {
        "response": serializer.data
    }

    return JsonResponse(response)

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
            "message": "Check-in data was successfully confirmed",
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
@require_http_methods(["POST"])
def confirm(request):
    try:
        request_body = json.loads(request.body)
        # Check if body?
        confirmation_list = request_body.get("confirmationList", [])

        attendance_entries = []

        # Check if there is an entry in db, but not in confirmation - then checked-in by mistake, delete (ONLY IF is_showed_up=True). Need a confirmation window?
        # Distinction between checked-in and No Show (24 hours policy, still need a record) and checked in by mistake (doesn't need a record)

        # If no difference in is_showed_up, then do nothing

        # Check confirmation by students to delete (in Attendance table, but not in request) and students to update is_showed_up (in table and in request)
        # So updating only the students who are both in table and request and have difference in is_showed_up, removing students who is in table, but not in request 

        for confirmation in confirmation_list:
            for student_id, classes_list in confirmation.items():
                for cls_id, show_up in classes_list.items():
                    if not Attendance.objects.filter(student_id=student_id, class_id=cls_id, attendance_date=now().date()).exists():
                        attendance_entries.append({
                            "student_id": student_id,
                            "class_id": cls_id,
                            "attendance_date": now().date(),
                            "is_showed_up": show_up,
                        })

        if attendance_entries:
            serializer = AttendanceSerializer(data=attendance_entries, many=True)
            if serializer.is_valid():
                serializer.save()
                return make_success_json_response(201, message="Attendance confirmed successfully")
            else:
                return make_error_json_response(serializer.errors, 400)
        else:
            return JsonResponse({"message": "No new attendance records to add"}, status=200)

    except json.JSONDecodeError:
        return make_error_json_response("Invalid JSON", 400)
    except Exception as e:
        return make_error_json_response(f"An unexpected error occurred: {e}", 500)


def report(request):
    return HttpResponse("Report view")

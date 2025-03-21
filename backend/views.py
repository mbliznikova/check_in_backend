import json

from datetime import datetime

from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now

from .models import ClassModel, Student, Day, Schedule, Attendance
from .serializers import StudentSerializer, ClassModelSerializer, AttendanceSerializer

def make_error_json_response(error_message, status_code):
    return JsonResponse({"error": error_message}, status=status_code)

def make_success_json_response(message, status_code):
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
        check_in_data = request_body.get("checkInData", {})
        student_id = check_in_data.get("studentId")
        classes_list = check_in_data.get("classesList")
        today_date = check_in_data.get("todayDate")

        if not student_id or not today_date:
            return make_error_json_response("Missing required fields", 400)

        existing_classes = set(Attendance.objects.filter(student_id=student_id, attendance_date=today_date).values_list("class_id", flat=True))
        classes_to_add = set(classes_list) - existing_classes
        classes_to_delete = existing_classes - set(classes_list)

        # Can reqrite to use Attendance.objects.create(), but then have to retrieve
        # instant of Student by student_id and pass as a FK
        for cls in classes_to_add:
            data_to_write = {
                    "student_id": student_id,
                    "class_id": cls,
                    "attendance_date": today_date,
                }
            serializer = AttendanceSerializer(data=data_to_write)
            if serializer.is_valid():
                serializer.save()
            else:
                return make_error_json_response(serializer.errors, 400)

        Attendance.objects.filter(student_id=student_id, attendance_date=today_date, class_id__in=classes_to_delete).delete()

        return make_success_json_response("Check-in data was successfully updated", 200)

    except json.JSONDecodeError:
        return make_error_json_response("Invalid JSON", 400)
    except Exception as e:
        return make_error_json_response(f"An unexpected error occurred: {e}", 500)

def get_attended_students(request):
    attended_today = Attendance.objects.filter(attendance_date=now().date())
    serializer = AttendanceSerializer(attended_today, many=True)
    response = {
        "response": serializer.data
    }
    return JsonResponse(response)

@csrf_exempt
@require_http_methods(["POST"])
def confirm(request):
    try:
        request_body = json.loads(request.body)
        confirmation_list = request_body.get("confirmationList", [])

        attendance_entries = []

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
                return make_success_json_response("Attendance confirmed successfully", 201)
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

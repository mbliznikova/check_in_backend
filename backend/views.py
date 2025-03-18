import json

from datetime import datetime

from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now

from .models import ClassModel, Student, Day, Schedule, Attendance
from .serializers import StudentSerializer, ClassModelSerializer, AttendanceSerializer

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

def check_in(request):
    # Receive, parse and validate the request body
    # Create a record in Attendance table
    # Send response?
    return HttpResponse("Check-in view")

@csrf_exempt
@require_http_methods(["POST"])
def confirm(request):
    try:
        request_body = json.loads(request.body)
        confirmation_list = request_body.get("confirmationList", [])

        attendance_entries = []

        for confirmation in confirmation_list:
            for student_id, classes_list in confirmation.items():
                for cls_id in classes_list:
                    if not Attendance.objects.filter(student_id=student_id, class_id=cls_id, attendance_date=now().date()).exists:
                        attendance_entries.append({
                            "student_id": student_id,
                            "class_id": cls_id,
                            "attendance_date": now().date(),
                            "is_showed_up": True,
                        })

        if attendance_entries:
            serializer = AttendanceSerializer(data=attendance_entries, many=True)
            if serializer.is_valid():
                serializer.save()
                return JsonResponse({"message": "Attendance confirmed successfully"}, status=201)
            else:
                return JsonResponse({"error": serializer.errors}, status=400)
        else:
            return JsonResponse({"message": "No new attendance records to add"}, status=200)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"An unexpected error occurred: {e}"}, status=500)


def report(request):
    return HttpResponse("Report view")

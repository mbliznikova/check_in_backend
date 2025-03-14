from datetime import datetime

from django.shortcuts import render
from django.http import HttpResponse, JsonResponse

from .models import ClassModel, Student, Day, Schedule
from .serializers import StudentSerializer, ClassModelSerializer

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
    # should return:
    return HttpResponse("Check-in view")

def confirm(request):
    return HttpResponse("Confirm view")

def report(request):
    return HttpResponse("Report view")

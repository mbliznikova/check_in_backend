from django.shortcuts import render
from django.http import HttpResponse, JsonResponse

from .models import ClassModel, Student

def classes_list(request):
    # return the list of all classes
    # filter based on what classes are scheduled for today?
    classes = {
        "response": [
            {
                "class_id": cls.class_id,
                "class_name": cls.name
            }
            for cls in ClassModel.objects.all()
        ]
    }

    return JsonResponse(classes)

def student_list(request):
    students = {
        "response": [
            {
                "student_id": student.student_id,
                "first_name": student.first_name,
                "last_name": student.last_name
            }
            for student in Student.objects.all()
        ]
    }

    return JsonResponse(students)

def check_in(request):
    # should return:
    return HttpResponse("Check-in view")

def confirm(request):
    return HttpResponse("Confirm view")

def report(request):
    return HttpResponse("Report view")

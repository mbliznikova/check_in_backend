from django.shortcuts import render
from django.http import HttpResponse, JsonResponse

from .models import ClassModel, Student
from .serializers import StudentSerializer, ClassModelSerializer

def classes_list(request):
    classes = ClassModel.objects.all()
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

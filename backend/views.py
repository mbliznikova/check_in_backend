from django.shortcuts import render
from django.http import HttpResponse

def check_in(request):
    return HttpResponse("Check-in view")

def confirm(request):
    return HttpResponse("Confirm view")

def report(request):
    return HttpResponse("Report view")

from django.urls import path

from . import views

urlpatterns = [
    path("", views.check_in, name="check_in"),
    path("check_in/", views.check_in, name="check_in"),
    path("confirm/", views.confirm, name="confirm"),
    path("report/", views.report, name="report"),
]
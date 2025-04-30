from django.urls import path

from . import views

urlpatterns = [
    path("", views.check_in, name="check_in"),
    path("check_in/", views.check_in, name="check_in"),
    path("confirm/", views.confirm, name="confirm"),
    path("attendances/", views.attendance_list, name="attendances"),
    path("report/", views.report, name="report"),
    path("classes/", views.classes_list, name="classes"),
    path("students/", views.student_list, name="students"),
    path("attended_sudents/", views.get_attended_students, name="attended_sudents"),
]
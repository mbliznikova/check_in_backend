from django.urls import path

from . import views

urlpatterns = [
    path("", views.check_in, name="check_in"),
    path("check_in/", views.check_in, name="check_in"),
    path("confirm/", views.confirm, name="confirm"),
    path("attendances/", views.attendance_list, name="attendances"),
    path("classes/", views.classes, name="classes"),
    path("today_classes_list/", views.today_classes_list, name="today_classes_list"),
    path("students/", views.students, name="students"),
    path("attended_sudents/", views.get_attended_students, name="attended_sudents"),
    path("prices/", views.prices_list, name="prices"),
    path("payments/", views.payments, name="payments"),
    path("payment_summary/", views.payment_summary, name="payment_summary"),
    path("schedules/", views.schedules, name="schedules"),
]
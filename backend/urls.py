from django.urls import path

from . import views

urlpatterns = [
    path("", views.check_in, name="check_in"),
    path("check_in/", views.check_in, name="check_in"),
    path("confirm/", views.confirm, name="confirm"),
    path("attendances/", views.attendance_list, name="attendances"),
    path("classes/", views.classes, name="classes"),
    path("today_classes_list/", views.today_classes_list, name="today_classes_list"),
    path("classes/<int:class_id>/edit/", views.edit_class, name="edit_class"),
    path("classes/<int:class_id>/delete/", views.delete_class, name="delete_class"),
    path("students/", views.students, name="students"),
    path("students/<int:student_id>/edit/", views.edit_student, name="edit_student"),
    path("students/<int:student_id>/delete/", views.delete_student, name="delete_student"),
    path("attended_sudents/", views.get_attended_students, name="attended_sudents"),
    path("prices/", views.prices_list, name="prices"),
    path("payments/", views.payments, name="payments"),
    path("payment_summary/", views.payment_summary, name="payment_summary"),
    path("schedules/", views.schedules, name="schedules"),
    path("schedules/<int:schedule_id>/delete/", views.delete_schedule, name="delete_schedule"),
]
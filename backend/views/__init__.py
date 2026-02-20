# Views package - domain-specific view modules
from backend.views.auth import get_user
from backend.views.classes import classes, today_classes_list, edit_class, delete_class
from backend.views.occurrences import (
    class_occurrences,
    today_class_occurrences,
    edit_occurrence,
    delete_occurrence,
)
from backend.views.schedules import schedules, delete_schedule, available_time_slots
from backend.views.students import students_view, list_students, create_student, edit_student, delete_student
from backend.views.attendance import check_in, get_attended_students, confirm, attendance_list
from backend.views.payments import prices, edit_price, payments, delete_payment, payment_summary
from backend.views.schools import schools, school_detail, edit_school, delete_school

__all__ = [
    "get_user",
    "classes",
    "today_classes_list",
    "edit_class",
    "delete_class",
    "class_occurrences",
    "today_class_occurrences",
    "edit_occurrence",
    "delete_occurrence",
    "schedules",
    "delete_schedule",
    "available_time_slots",
    "students_view",
    "list_students",
    "create_student",
    "edit_student",
    "delete_student",
    "check_in",
    "get_attended_students",
    "confirm",
    "attendance_list",
    "prices",
    "edit_price",
    "payments",
    "delete_payment",
    "payment_summary",
    "schools",
    "school_detail",
    "edit_school",
    "delete_school",
]

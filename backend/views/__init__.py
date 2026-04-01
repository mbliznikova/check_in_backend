# Views package - domain-specific view modules
from backend.views.attendance import (
    attendance_list, check_in, confirm, get_attended_students,
)
from backend.views.auth import get_user
from backend.views.classes import (
    classes, delete_class, edit_class, today_classes_list,
)
from backend.views.occurrences import (
    class_occurrences, delete_occurrence, edit_occurrence,
    today_class_occurrences,
)
from backend.views.payments import (
    delete_payment, edit_price, payment_summary, payments, prices,
)
from backend.views.schedules import (
    available_time_slots, delete_schedule, schedules,
)
from backend.views.schools import (
    delete_school, edit_school, school_detail, schools,
)
from backend.views.students import (
    create_student, delete_student, edit_student, list_students, students_view,
)

from backend.views.invitations import (
    create_invitation, accept_invitation,
)

from backend.views.memberships import (
    list_memberships, edit_membership, delete_membership,
)

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
    "create_invitation",
    "accept_invitation",
    "list_memberships",
    "edit_membership",
    "delete_membership",
]

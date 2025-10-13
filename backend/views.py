import json

from datetime import date, datetime, timedelta

from django.db.models import Q, Sum
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now, is_naive, make_aware
from django.utils.dateparse import parse_datetime, parse_time
from django.core.exceptions import ObjectDoesNotExist

from .models import ClassModel, Student, Day, Schedule, Attendance, Price, Payment, ClassOccurrence
from .serializers import CaseSerializer, StudentSerializer, ClassModelSerializer, AttendanceSerializer, PaymentSerializer, MonthlyPaymentsSummary, ScheduleSerializer, ClassOccurrenceSerializer

# TODO: have parameters more consistent, i.e. have status code at the same order
def make_error_json_response(error_message, status_code):
    return JsonResponse({"error": error_message}, status=status_code)

def make_success_json_response(status_code, message="Success", response_body=None):
    if response_body:
        return JsonResponse(response_body, status=status_code)
    return JsonResponse({"message": message}, status=status_code)

# TODO: should I move it to schedules and just have a query parameter?
def today_classes_list(request):
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

@csrf_exempt
@require_http_methods(["GET", "POST"])
def classes(request):
    if request.method == "GET":
        classes = ClassModel.objects.all()
        serializer = ClassModelSerializer(classes, many=True)

        response = {
            "response": serializer.data
        }

        return JsonResponse(response)
    if request.method == "POST":
        try:
            request_body = json.loads(request.body)
            name = request_body.get("name", "")
            duration_minutes = request_body.get("durationMinutes")

            if not name:
                return make_error_json_response("Class name should not be empty", 400)

            data_to_write = {
                "name": name
            }

            if duration_minutes is not None:
                data_to_write["duration_minutes"] = duration_minutes

            serializer = ClassModelSerializer(data=data_to_write)
            if serializer.is_valid():
                saved_class = serializer.save()
            else:
                return make_error_json_response(serializer.errors, 400)

            response = ClassModelSerializer.dict_to_camel_case( # for the case there will be camel case in the future
                {
                    "message": "Class was created successfully",
                    "id": saved_class.id,
                    "name": saved_class.name,
                    "duration_minutes": saved_class.duration_minutes,
                }
            )

            return make_success_json_response(200, response_body=response)

        except json.JSONDecodeError:
            return make_error_json_response("Invalid JSON", 400)
        except Exception as e:
            return make_error_json_response(f"An unexpected error occurred: {e}", 500)

def today_class_occurrences(request):
    today_day = date.today()
    occurrences = ClassOccurrence.objects.filter(Q(planned_date=today_day) | Q(actual_date=today_day))

    serializer = ClassOccurrenceSerializer(occurrences, many=True)

    response = {
        "response": serializer.data
    }

    return make_success_json_response(200, response_body=response)

@csrf_exempt
@require_http_methods(["PUT"])
def edit_class(request, class_id):
    if request.method == "PUT":
        try:
            class_instance = ClassModel.objects.get(id=class_id)

            request_body = json.loads(request.body)
            class_name = request_body.get("name")
            duration_minutes = request_body.get("durationMinutes")

            # TODO: update tests

            if class_name is not None:
                if not class_name.strip():
                    return make_error_json_response("Class name cannot be empty", 400)
                class_instance.name = class_name

            if duration_minutes is not None: # TODO: add checks?
                class_instance.duration_minutes = duration_minutes

            class_instance.save()

            response = ClassModelSerializer.dict_to_camel_case(
                {
                    "message": "Class was updated successfully",
                    "class_id": class_instance.id,
                    "class_name": class_instance.name,
                    "duration_minutes": class_instance.duration_minutes,
                }
            )

            return make_success_json_response(200, response_body=response)

        except ClassModel.DoesNotExist:
            return make_error_json_response("Class not found", 404)
        except json.JSONDecodeError:
            return make_error_json_response("Invalid JSON", 400)
        except Exception as e:
            return make_error_json_response(f"An unexpected error occurred: {e}", 500)

@csrf_exempt
@require_http_methods(["DELETE"])
def delete_class(request, class_id):
    if request.method == "DELETE":
        try:
           class_instance = ClassModel.objects.get(id=class_id)
           class_instance_id = class_instance.id
           class_instance_name = class_instance.name

           class_instance.delete()

           response = ClassModelSerializer.dict_to_camel_case(
                {
                    "message": f"Class {class_instance_id} - {class_instance_name} was delete successfully",
                    "class_id": class_instance_id,
                    "class_name": class_instance_name,
                }
            )

           return make_success_json_response(200, response_body=response)

        except ClassModel.DoesNotExist:
            return make_error_json_response("Class not found", 404)
        except Exception as e:
            return make_error_json_response(f"An unexpected error occurred: {e}", 500)

@csrf_exempt
@require_http_methods(["DELETE"])
def delete_schedule(request, schedule_id):
    if request.method == "DELETE":
        try:
            schedule_instance = Schedule.objects.get(id=schedule_id)
            schedule_instance_id = schedule_instance.id

            schedule_instance.delete()

            response = ScheduleSerializer.dict_to_camel_case(
                {
                    "message": f"Schedule {schedule_instance_id} was delete successfully",
                    "schedule_id": schedule_instance_id,
                }
            )

            return make_success_json_response(200, response_body=response)

        except Schedule.DoesNotExist:
            return make_error_json_response("Schedule not found", 404)
        except Exception as e:
            return make_error_json_response(f"An unexpected error occurred: {e}", 500)

@csrf_exempt
@require_http_methods(["GET", "POST"])
def schedules(request):
    if request.method == "GET":
        class_id = request.GET.get("class_id")
        if class_id:
            schedules = Schedule.objects.filter(class_model=class_id)
        else:
            schedules = Schedule.objects.all()
        serializer = ScheduleSerializer(schedules, many=True)

        response = {
            "response": serializer.data
        }

        return JsonResponse(response)

    if request.method == "POST":
        try:
            request_body = json.loads(request.body)
            class_id = request_body.get("classId", "")
            day_name = request_body.get("day", "")
            class_time_str = request_body.get("classTime", "")

            if not class_id or not day_name or not class_time_str:
                return make_error_json_response("Missing required fields", 400)

            try:
                class_model = ClassModel.objects.get(id=class_id)
            except ClassModel.DoesNotExist:
                return make_error_json_response("Class not found", 404)

            try:
                day = Day.objects.get(name=day_name)
            except Day.DoesNotExist:
                return make_error_json_response("Day not found", 404)

            try:
                parsed_time = parse_time(class_time_str)
                if not parsed_time:
                    return make_error_json_response("Invalid time format", 400)
            except (ValueError, TypeError):
                return make_error_json_response("Invalid time format", 400)

            data_to_write = {
                "class_model": class_model.id,
                "day": day.id,
                "class_time": parsed_time
            }

            serializer = ScheduleSerializer(data=data_to_write)
            if serializer.is_valid():
                saved_schedule = serializer.save()
            else:
                return make_error_json_response(serializer.errors, 400)

            response = ScheduleSerializer.dict_to_camel_case(
                {
                    "message": "Schedule was created successfully",
                    "schedule_id": saved_schedule.id,
                    "class_id": saved_schedule.class_model.id,
                    "class_name": saved_schedule.class_model.name,
                    "day": saved_schedule.day.name,
                    "time": saved_schedule.class_time,
                }
            )

            return make_success_json_response(200, response_body=response)

        # TODO: add check for attempt to schedule the class to already existing schedule, see issue #2

        except json.JSONDecodeError:
            return make_error_json_response("Invalid JSON", 400)
        except Exception as e:
            return make_error_json_response(f"An unexpected error occurred: {e}", 500)

@csrf_exempt
@require_http_methods(["GET"])
def available_time_slots(request):
    day_param = request.GET.get("day")
    duration_minutes_param = request.GET.get("duration")

    if not day_param:
        return make_error_json_response("Day was not provided", 400)
    if not duration_minutes_param:
        return make_error_json_response("Class duration was not provided", 400)

    try:
        duration_minutes = int(duration_minutes_param)
        if duration_minutes <= 0:
            return make_error_json_response("Class duration must be positive", 400)
    except ValueError:
        return make_error_json_response("Invalid duration_minutes format", 400)

    try:
        day_obj = Day.objects.get(name__iexact=day_param.strip())
    except ObjectDoesNotExist:
        return make_error_json_response(f"Day {day_param} does not exist", 400)

    schedules = Schedule.objects.filter(day=day_obj)

    available_slots = calculate_available_time_slots(schedules, duration_minutes)

    response = CaseSerializer.dict_to_camel_case(
        {
            "message": "Available time slots",
            "available_slots": available_slots,
        }
    )

    return make_success_json_response(200, response_body=response)

# TODO: have defaults set globally
def calculate_available_time_slots(schedules, duration_to_fit, step_minutes=30,
                                   day_start="08:00", day_end="21:00"):
    available_slots, taken_slots = [], []
    base_date = datetime.today().date() # Can't substract datetime.time: convert to datetime.datetime

    dummy_day_start_class = datetime.combine(base_date, datetime.strptime(day_start, "%H:%M").time())
    dummy_day_end_class = datetime.combine(base_date, datetime.strptime(day_end, "%H:%M").time())
    taken_slots.append({"start_time": dummy_day_start_class, "end_time": dummy_day_start_class})

    for schedule in schedules:
        start_time = datetime.combine(base_date, schedule.class_time)
        class_duration = schedule.class_model.duration_minutes
        end_time = start_time + timedelta(minutes=class_duration)
        taken_slots.append({"start_time": start_time, "end_time": end_time})

    taken_slots.append({"start_time": dummy_day_end_class, "end_time": dummy_day_end_class})

    len_taken_slots = len(taken_slots)

    taken_slots = sorted(taken_slots, key=lambda x: x["start_time"])

    for i in range (len_taken_slots - 1):
        window_start = taken_slots[i]["end_time"]
        window_end = taken_slots[i + 1]["start_time"]

        time_interval = window_end - window_start
        interval_minutes = int(time_interval.total_seconds() // 60)

        if interval_minutes < duration_to_fit:
            continue
        else:
            duration = timedelta(minutes=duration_to_fit)
            step = timedelta(minutes=step_minutes)
            candidate_start = window_start

            while candidate_start + duration <= window_end:
                available_slots.append(candidate_start.time().strftime("%H:%M"))
                candidate_start += step

    return available_slots

@csrf_exempt
@require_http_methods(["GET", "POST"])
def students(request):
    if request.method == "GET":
        students = Student.objects.all()
        serializer = StudentSerializer(students, many=True)

        response = {
            "response": serializer.data
        }

        return JsonResponse(response)

    if request.method == "POST":
        try:
            request_body = json.loads(request.body)
            first_name = request_body.get("firstName", "")
            last_name = request_body.get("lastName", "")
            is_liability_form_sent = request_body.get("isLiabilityFormSent")
            emergency_contacts = request_body.get("emergencyContacts")

            if not first_name or not last_name:
                return make_error_json_response("First and last name should not be empty", 400)

            data_to_write = {
                "first_name": first_name,
                "last_name": last_name,
            }

            if is_liability_form_sent is not None:
                data_to_write["is_liability_form_sent"] = is_liability_form_sent

            if emergency_contacts is not None:
                data_to_write["emergency_contacts"] = emergency_contacts

            serializer = StudentSerializer(data=data_to_write)
            if serializer.is_valid():
                saved_student = serializer.save()
            else:
                return make_error_json_response(serializer.errors, 400)

            respone = StudentSerializer.dict_to_camel_case(
                {
                    "message": "Student was created successfully",
                    "student_id": saved_student.id,
                    "first_name": saved_student.first_name,
                    "last_name": saved_student.last_name,
                    "is_liability_form_sent": saved_student.is_liability_form_sent,
                    "emergency_contacts": saved_student.emergency_contacts,
                }
            )

            return make_success_json_response(200, response_body=respone)

        except json.JSONDecodeError:
            return make_error_json_response("Invalid JSON", 400)
        except Exception as e:
            return make_error_json_response(f"An unexpected error occurred: {e}", 500)

@csrf_exempt
@require_http_methods(["PUT"])
def edit_student(request, student_id):
    if request.method == "PUT":
        try:
            student_instance = Student.objects.get(id=student_id)

            request_body = json.loads(request.body)
            first_name = request_body.get("firstName")
            last_name = request_body.get("lastName")
            is_liability_form_sent = request_body.get("isLiabilityFormSent")
            emergency_contacts = request_body.get("emergencyContacts")

            if first_name is not None:
                if not first_name.strip():
                    return make_error_json_response("First name cannot be empty", 400)
                student_instance.first_name = first_name

            if last_name is not None:
                if not last_name.strip():
                    return make_error_json_response("Last name cannot be empty", 400)
                student_instance.last_name = last_name

            if is_liability_form_sent is not None:
                student_instance.is_liability_form_sent = is_liability_form_sent

            if emergency_contacts is not None:
                student_instance.emergency_contacts = emergency_contacts

            student_instance.save()

            #TODO: update the tests

            response = StudentSerializer.dict_to_camel_case(
                {
                    "message": f"Student {student_instance.id} was updated successfully",
                    "student_id": student_instance.id,
                    "first_name": student_instance.first_name,
                    "last_name": student_instance.last_name,
                    "is_liability_form_sent": student_instance.is_liability_form_sent,
                    "emergency_contacts": student_instance.emergency_contacts,
                }
            )

            return make_success_json_response(200, response_body=response)

        except Student.DoesNotExist:
            return make_error_json_response("Student not found", 404)
        except json.JSONDecodeError:
            return make_error_json_response("Invalid JSON", 400)
        except Exception as e:
            return make_error_json_response(f"An unexpected error occurred: {e}", 500)

@csrf_exempt
@require_http_methods(["DELETE"])
def delete_student(request, student_id):
    if request.method == "DELETE":
        try:
            student_instance = Student.objects.get(id=student_id)
            student_instance_id = student_instance.id

            student_instance.delete()

            response = StudentSerializer.dict_to_camel_case(
                {
                    "message": f"Student {student_instance_id} was delete successfully",
                    "student_id": student_instance_id,
                }
            )

            return make_success_json_response(200, response_body=response)

        except Schedule.DoesNotExist:
            return make_error_json_response("Student not found", 404)
        except Exception as e:
            return make_error_json_response(f"An unexpected error occurred: {e}", 500)

@csrf_exempt
@require_http_methods(["POST"])
def check_in(request):
    # For now this view serves for insertion and deletion entries to/from Attendance table since the data with classes
    # a student attends to arrives complete every time, like a source of truth
    try:
        request_body = json.loads(request.body)
        # Check if body?
        check_in_data = request_body.get("checkInData", {})
        student_id = check_in_data.get("studentId")
        classes_list = check_in_data.get("classesList", []) # TODO: class_occurences_list? Have occurrence for each class?
        class_occurrences_list = check_in_data.get("classOccurrencesList", [])
        today_date = check_in_data.get("todayDate")

        if not student_id or not today_date:
            return make_error_json_response("Missing required fields", 400)

        use_occurrence = bool(class_occurrences_list) # Use if provided, otherwise fall back to classes_list. Transition.

        if use_occurrence:
            print("CHECK-IN DEBUG! USING OCCURRENCES!")
            existing_occurrences = set(Attendance.objects.filter(student_id=student_id, attendance_date=today_date).values_list("class_occurrence", flat=True))
            to_add = set(class_occurrences_list) - existing_occurrences
            to_delete = existing_occurrences - set(class_occurrences_list)

            to_add_response, to_delete_response = [], []

            for occ in to_add:
                data_to_write = {
                    "student_id": student_id,
                    "class_occurrence": occ,
                    # "class_id": classes_list[0] if classes_list else 3, # TODO: REMOVE class_id field from Attendance model when ready
                    "attendance_date": today_date,
                }

                serializer = AttendanceSerializer(data=data_to_write)
                print(f"DEBUG! To add is {data_to_write}")

                if serializer.is_valid():
                    serializer.save()
                    to_add_response.append(occ)
                else:
                    return make_error_json_response(serializer.errors, 400)

            if to_delete:
                print(f"DEBUG! To delete is {Attendance.objects.filter(student_id=student_id, attendance_date=today_date, class_occurrence__in=to_delete)}")
                Attendance.objects.filter(student_id=student_id, attendance_date=today_date, class_occurrence__in=to_delete).delete()

                for occ in to_delete:
                    to_delete_response.append(occ)

        else:
            print("CHECK-IN DEBUG! USING CLASSES!")
            # TODO: add parsing for today_date
            existing_classes = set(Attendance.objects.filter(student_id=student_id, attendance_date=today_date).values_list("class_id", flat=True))
            classes_to_add = set(classes_list) - existing_classes
            classes_to_delete = existing_classes - set(classes_list)

            classes_to_add_response, classes_to_delete_response = [], []

            # Can rewrite to use Attendance.objects.create() instead of using serializer, but then have to retrieve
            # instance of Student by student_id and pass as a FK
            for cls in classes_to_add:
                data_to_write = {
                        "student_id": student_id,
                        "class_id": cls,
                        "attendance_date": today_date,
                    }
                serializer = AttendanceSerializer(data=data_to_write)
                if serializer.is_valid():
                    serializer.save()
                    classes_to_add_response.append(cls)
                else:
                    return make_error_json_response(serializer.errors, 400)

            if classes_to_delete:
                Attendance.objects.filter(student_id=student_id, attendance_date=today_date, class_id__in=classes_to_delete).delete()

                for cls in classes_to_delete:
                    classes_to_delete_response.append(cls)

        response = CaseSerializer.dict_to_camel_case(
            {
                "message": "Check-in data was successfully updated",
                "student_id": student_id,
                "attendance_date": today_date,
                "checked_in": classes_to_add_response if not use_occurrence else to_add_response,
                "checked_out": classes_to_delete_response  if not use_occurrence else to_delete_response,
            })

        return make_success_json_response(200, response_body=response)

    except json.JSONDecodeError:
        return make_error_json_response("Invalid JSON", 400)
    except Exception as e:
        return make_error_json_response(f"An unexpected error occurred: {e}", 500)

def get_attended_students(request):
    attended_today = Attendance.objects.filter(attendance_date=now().date())
    student_class_ids = attended_today.values_list("student_id", "class_id")
    student_occurrence_ids = attended_today.values_list("student_id", "class_occurrence", "class_name") # new

    student_classes = {}
    student_occurrence = {} # new

    for student_id, class_id in student_class_ids:
        student_classes.setdefault(student_id, []).append(class_id)

    for student_id, occurrence_id, class_name in student_occurrence_ids: # new
        student_occurrence.setdefault(student_id, []).append([occurrence_id, class_name])

    students_attended_today = Student.objects.filter(id__in=student_classes.keys())
    students_attended_today_occ = Student.objects.filter(id__in=student_occurrence.keys()) # new

    response = CaseSerializer.dict_to_camel_case(
        {
            "confirmed_attendance":
            [
                CaseSerializer.dict_to_camel_case({
                    "id": student.id,
                    "first_name": student.first_name,
                    "last_name": student.last_name,
                    "classes": student_classes.get(student.id, []),
                })
                for student in students_attended_today
            ]
        })
    # print(f"get_attended_students DEBUG! OLD! response is {response}")

    response_new = CaseSerializer.dict_to_camel_case(  # new
        {
            "confirmed_attendance":
            [
                CaseSerializer.dict_to_camel_case({
                    "id": student.id,
                    "first_name": student.first_name,
                    "last_name": student.last_name,
                    "occurrences": [occ[0] for occ in student_occurrence.get(student.id, [])],
                    "class_name": [occ[-1] for occ in student_occurrence.get(student.id, [])],
                })
                for student in students_attended_today_occ
            ]
        })
    # print(f"get_attended_students DEBUG! NEW! response_new is {response_new}")

    return make_success_json_response(200, response_body=response)

@csrf_exempt
@require_http_methods(["PUT"])
def confirm(request):
    try:
        request_body = json.loads(request.body)

        confirmation_list = request_body.get("confirmationList", []) # TODO: have the same format for class occurrence. But maybe also class name also? 
        # TODO: what would be the default today_date value?
        confirmation_day = request_body.get("date", now().date())

        attended_today = Attendance.objects.filter(attendance_date=confirmation_day)

        if not isinstance(confirmation_list, list):
            return make_error_json_response("Invalid data format: 'confirmationList' should be a list", 400)

        confirmed_attendance = {}
        confirmed_attendance_new = {}

        for confirmation in confirmation_list:
            if not isinstance(confirmation, dict):
                return make_error_json_response("Invalid data format: Each item in 'confirmationList' should be a dictionary", 400)
            confirmed_attendance.update(confirmation)

        for confirmation in confirmation_list:
            if not isinstance(confirmation, dict):
                return make_error_json_response("Invalid data format: Each item in 'confirmationList' should be a dictionary", 400)
            confirmed_attendance_new.update(confirmation)

        confirmed_attendance = {
            int(student_id_key): {
                    int(class_id_key): bool(value) for class_id_key, value in classes.items()
                }
                for student_id_key, classes in confirmed_attendance.items()
        }
        print(f"DEBUG confirm OLD confirmed_attendance is {confirmed_attendance}")

        confirmed_attendance_new = { # NEW
            int(student_id_key): {
                    int(occurrence_id_key): bool(value) for occurrence_id_key, value in occurrences.items()
                }
                for student_id_key, occurrences in confirmed_attendance_new.items()
        }
        print(f"DEBUG confirm NEW confirmed_attendance_new is {confirmed_attendance_new}")

        attendance_to_delete, attendance_to_update = [], []
        to_delete, to_update = [], []

        for attendance in attended_today:
            student_id = attendance.safe_student_id # TODO: add more checks
            class_id = attendance.safe_class_id

            if student_id not in confirmed_attendance or class_id not in confirmed_attendance[student_id]:
                attendance_to_delete.append(attendance.id)
                continue

            new_is_showed_up_value = confirmed_attendance.get(student_id, {}).get(class_id)

            if attendance.is_showed_up != new_is_showed_up_value:
                attendance.is_showed_up = new_is_showed_up_value
                attendance_to_update.append(attendance)

        print(f"DEBUG OLD attendance_to_update {attendance_to_update}, attendance_to_delete {attendance_to_delete}")

        # ====== NEW
        for attendance in attended_today:
            student_id = attendance.safe_student_id # TODO: add more checks
            occurrence_id = attendance.safe_occurrence_id # <--- do we need it? Shouldn't it be rather name? 

            if student_id not in confirmed_attendance_new or occurrence_id not in confirmed_attendance_new[student_id]:
                to_delete.append(attendance.id)
                continue

            new_is_showed_up_value = confirmed_attendance_new.get(student_id, {}).get(occurrence_id)

            if attendance.is_showed_up != new_is_showed_up_value:
                attendance.is_showed_up = new_is_showed_up_value
                to_update.append(attendance)

        print(f"DEBUG NEW to_update {to_update}, to_delete {to_delete}")
        # ======

        if attendance_to_delete:
            Attendance.objects.filter(id__in=attendance_to_delete).delete()

        if attendance_to_update:
            Attendance.objects.bulk_update(attendance_to_update, ["is_showed_up"])

        response = {
            "message": "Attendance confirmed successfully"
        }

        return make_success_json_response(200, response_body=response)

    except json.JSONDecodeError:
        return make_error_json_response("Invalid JSON", 400)
    except Exception as e:
        return make_error_json_response(f"An unexpected error occurred: {e}", 500)

def attendance_list(request):
    request_month = request.GET.get("month")
    request_year = request.GET.get("year")

    attendances = None

    if request_month and request_year:
        try:
            request_month = int(request_month)
            request_year = int(request_year)

            # TODO: add tests

            if not (1 <= request_month <= 12):
                return make_error_json_response(f"Month must be between 1 and 12, not {request_month}", 400)

            # TODO: think about acceptable year range
            if not (2000 <= request_year <= now().year + 1):
                return make_error_json_response(f"Invalid year: {request_year}", 400)

            attendances = Attendance.objects.all().order_by("-attendance_date").filter(
                attendance_date__month=request_month,
                attendance_date__year=request_year
            )
        except ValueError:
            return make_error_json_response("Invalid month or year", 400)
    else:
        attendances = Attendance.objects.all().order_by("-attendance_date")

        # print(f"================DEBUG!!! attendances is {attendances}================")

    attendance_dict = {}
    attendance_dict_new = {} # NEW

    for att in attendances:
        str_date = att.attendance_date.isoformat()
        str_class_id = str(att.safe_class_id or "")
        str_class_name = att.class_name or ""
        str_student_id = str(att.safe_student_id or "")
        str_student_first_name = att.student_first_name or ""
        str_student_last_name = att.student_last_name or ""
        str_occurrence = str(att.class_occurrence or "") # NEW
        # print(f"DEBUG attendance_list: str_occurrence is {str_occurrence}") #TODO: have safe class occurrence in right format, see str_class_id = str(att.safe_class_id or "")

        if str_date not in attendance_dict:
            attendance_dict[str_date] = {}


        if str_date not in attendance_dict_new: # NEW
            attendance_dict_new[str_date] = {}

        if str_class_id not in attendance_dict[str_date]:
           attendance_dict[str_date][str_class_id] = {
               "name": str_class_name,
               "students": {}
           }

        # ======= NEW
        if str_occurrence not in attendance_dict_new[str_date]: # NEW
           attendance_dict_new[str_date][str_occurrence] = {
               "name": str_class_name,
               "students": {}
           }
        # =======

        attendance_dict[str_date][str_class_id]["students"][str_student_id] = CaseSerializer.dict_to_camel_case({
            "first_name": str_student_first_name,
            "last_name": str_student_last_name,
            "is_showed_up": att.is_showed_up
        })
        # print(f"DEBUG OLD attendance_list! attendance_dict is {attendance_dict}")

        # ======= NEW
        attendance_dict_new[str_date][str_occurrence]["students"][str_student_id] = CaseSerializer.dict_to_camel_case({ # NEW
            "first_name": str_student_first_name,
            "last_name": str_student_last_name,
            "is_showed_up": att.is_showed_up
        })
        # =======
        # print(f"DEBUG NEW attendance_list! attendance_dict_new is {attendance_dict_new}")

    # TODO: Write tests

    result_list = []
    for date, class_data in attendance_dict.items():
        result_list.append(
            CaseSerializer.dict_to_camel_case({
                "date": date,
                "classes": class_data,
            })
        )
    # print(f"DEBUG OLD attendance_list! result_list is {result_list}")

    # ======= NEW
    result_list_new = []
    for date, class_data in attendance_dict_new.items():
        result_list_new.append(
            CaseSerializer.dict_to_camel_case({
                "date": date,
                "classes": class_data,
            })
        )
    # =======
    # print(f"DEBUG NEW attendance_list! esult_list_new is {result_list_new}")

    response = {
        "response": result_list
    }

    return make_success_json_response(200, response_body=response)

def prices_list(request):
    prices = Price.objects.all()

    price_dict = {}
    for price in prices:
        price_dict[str(price.class_id.id)] = {price.class_id.name: price.amount}

    response = {
        "response": price_dict
    }

    return make_success_json_response(200, response_body=response)

@csrf_exempt
@require_http_methods(["GET", "POST"])
def payments(request):
    if request.method == "GET":
        payment_month_param = request.GET.get('month', now().month)
        payment_year_param = request.GET.get('year', now().year)
        payments = Payment.objects.all().filter(
            payment_month = payment_month_param,
            payment_year = payment_year_param)
        serializer = PaymentSerializer(payments, many=True)

        response = {
            "response": serializer.data
        }

        return make_success_json_response(200, response_body=response)

    if request.method == "POST":
        try:
            request_body = json.loads(request.body)
            payment_data = request_body.get("paymentData", {})
            student_id = payment_data.get("studentId")
            class_id = payment_data.get("classId")
            student_name = payment_data.get("studentName")
            class_name = payment_data.get("className")
            amount = payment_data.get("amount")
            payment_date_str = payment_data.get("paymentDate")
            month = payment_data.get("month")
            year = payment_data.get("year")

            if not student_id or not class_id or not amount:
                return make_error_json_response("Missing required fields", 400)

            if not month or not year:
                return make_error_json_response("Missing required fields", 400)

            if not student_name:
                try:
                    student = Student.objects.get(id=student_id)
                    student_name = f"{student.first_name} {student.last_name}"
                except Student.DoesNotExist:
                    return make_error_json_response("Student not found", 404)

            if not class_name:
                try:
                    cls = ClassModel.objects.get(id=class_id)
                    class_name = f"{cls.name}"
                except ClassModel.DoesNotExist:
                    return make_error_json_response("Class not found", 404)

            payment_date = parse_datetime(payment_date_str) if payment_date_str else None

            if payment_date is None and payment_date_str:
                return make_error_json_response("Invalid datetime format for payment date", 400)

            if not isinstance(month, int) or not isinstance(year, int):
                return make_error_json_response("Invalid date format for month or year", 400)

            if not (1 <= month <= 12):
                return make_error_json_response("Invalid value for month: should be between 1 and 12", 400)

            # TODO: the way to validate the value of the year: how far backward/forward?

            # TODO: handle time zones?
            if payment_date and is_naive(payment_date):
                payment_date = make_aware(payment_date)

            data_to_write = {
                "student_id": student_id,
                "class_id": class_id,
                "student_name": student_name,
                "class_name": class_name,
                "amount": amount,
                "payment_month": month,
                "payment_year": year,
            }

            if payment_date:
                data_to_write["payment_date"] = payment_date

            serializer = PaymentSerializer(data=data_to_write)

            if serializer.is_valid():
                saved_payment = serializer.save()
            else:
                return make_error_json_response(serializer.errors, 400)

            response = PaymentSerializer.dict_to_camel_case(
                {
                    "message": "Payment was successfully created",
                    "payment_id": saved_payment.id,
                    "student_id": saved_payment.student_id.id if saved_payment.student_id else None,
                    "class_id": saved_payment.class_id.id if saved_payment.class_id else None,
                    "student_name": saved_payment.student_name,
                    "class_name": saved_payment.class_name,
                    "amount": saved_payment.amount,
                    "payment_date": saved_payment.payment_date.isoformat(),
                    "payment_month": saved_payment.payment_month,
                    "payment_year": saved_payment.payment_year,
                }
            )

            return make_success_json_response(200, response_body=response)

        except json.JSONDecodeError:
            return make_error_json_response("Invalid JSON", 400)

def payment_summary(request):
    # By default returns for the current month (for now)
    # Should I calculate it from payments? Every time or by a separate request only?
    # If there is an existing entry - compare and recalculate if needed

    payment_month_param = request.GET.get("month", now().month)
    payment_year_param = request.GET.get("year", now().year)

    payment_summary = Payment.objects.filter(
        payment_year = payment_year_param,
        payment_month = payment_month_param
    )

    new_summary = payment_summary.aggregate(Sum("amount"))["amount__sum"] or 0.0

    # TODO: handle logic to add new entry for MonthlyPaymentsSummary or update the existing one
    # if new_summary != old_summary or not old_summary:
    old_summary = MonthlyPaymentsSummary.objects.filter(
        summary_date__year = now().year,
        summary_date__month = now().month
    )

    summary = {"summary": new_summary}

    response = {
        "response": summary
    }

    return make_success_json_response(200, response_body=response)

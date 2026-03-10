import json
from datetime import datetime, timedelta

from django.utils.dateparse import parse_date, parse_time
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from backend.decorators import teacher_or_above
from backend.models import ClassModel, ClassOccurrence, Day, Schedule
from backend.serializers import CaseSerializer, ScheduleSerializer
from backend.views.helpers import (
    DEFAULT_DAY_END_TIME,
    DEFAULT_DAY_START_TIME,
    DEFAULT_TIME_SLOT_STEP_MINUTES,
    make_error_json_response,
    make_success_json_response,
)


@teacher_or_above
@csrf_exempt
@require_http_methods(["GET"])
def available_occurrence_time(request):
    date_param = request.GET.get("date")
    duration_minutes_param = request.GET.get("duration")

    if not date_param:
        return make_error_json_response("Date was not provided", 400)
    if not duration_minutes_param:
        return make_error_json_response("Class duration was not provided", 400)

    parsed_date = parse_date(date_param)
    if not parsed_date:
        return make_error_json_response("Invalid date format", 400)

    try:
        duration_minutes = int(duration_minutes_param)
        if duration_minutes <= 0:
            return make_error_json_response(
                "Class duration must be positive", 400)
    except ValueError:
        return make_error_json_response("Invalid duration_minutes format", 400)

    occurrences = ClassOccurrence.objects.filter(
        actual_date=parsed_date,
        school=request.school,
    )

    available_slots = calculate_available_occurrence_time_intervals(
        occurrences, duration_minutes, parsed_date)

    response = CaseSerializer.dict_to_camel_case({
        "message": "Available time intervals for class occurrence",
        "available_intervals": available_slots,
    })

    return make_success_json_response(200, response_body=response)


def calculate_available_occurrence_time_intervals(
        occurrences,
        duration_to_fit,
        base_date,
        day_start=None,
        day_end=None):
    if day_start is None:
        day_start = DEFAULT_DAY_START_TIME
    if day_end is None:
        day_end = DEFAULT_DAY_END_TIME
    available_intervals, taken_intervals = [], []

    dummy_day_start_class = datetime.combine(
        base_date, datetime.strptime(
            day_start, "%H:%M").time())
    dummy_day_end_class = datetime.combine(
        base_date, datetime.strptime(
            day_end, "%H:%M").time())
    taken_intervals.append(
        {"start_time": dummy_day_start_class, "end_time": dummy_day_start_class})

    for occurrence in occurrences:
        start_time = datetime.combine(base_date, occurrence.actual_start_time)
        class_duration = occurrence.actual_duration
        end_time = start_time + timedelta(minutes=class_duration)
        taken_intervals.append(
            {"start_time": start_time, "end_time": end_time})

        last_occurrence_start = datetime.combine(
            base_date, occurrence.actual_start_time)
        dummy_day_end_class = last_occurrence_start if last_occurrence_start > dummy_day_end_class else dummy_day_end_class

    taken_intervals.append(
        {"start_time": dummy_day_end_class, "end_time": dummy_day_end_class})

    len_taken_intervals = len(taken_intervals)

    taken_intervals = sorted(taken_intervals, key=lambda x: x["start_time"])

    for i in range(len_taken_intervals - 1):
        window_start = taken_intervals[i]["end_time"]
        window_end = taken_intervals[i + 1]["start_time"]

        time_interval = window_end - window_start
        interval_minutes = int(time_interval.total_seconds() // 60)

        if interval_minutes < duration_to_fit:
            continue
        else:
            duration = timedelta(minutes=duration_to_fit)
            available_intervals.append([window_start.time().strftime(
                "%H:%M"), (window_end - duration).time().strftime("%H:%M")])

    return available_intervals


@teacher_or_above
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_schedule(request, schedule_id):
    if request.method == "DELETE":
        try:
            schedule_instance = Schedule.objects.get(
                id=schedule_id,
                school=request.school,
            )
            schedule_instance_id = schedule_instance.id

            schedule_instance.delete()

            response = ScheduleSerializer.dict_to_camel_case({
                "message": f"Schedule {schedule_instance_id} was deleted successfully",
                "schedule_id": schedule_instance_id,
            })

            return make_success_json_response(200, response_body=response)

        except Schedule.DoesNotExist:
            return make_error_json_response("Schedule not found", 404)
        except Exception:
            return make_error_json_response("An internal error occurred", 500)


@teacher_or_above
@csrf_exempt
@require_http_methods(["GET", "POST"])
def schedules(request):
    if request.method == "GET":
        class_id = request.GET.get("class_id")
        if class_id:
            schedules = Schedule.objects.filter(
                class_model=class_id,
                school=request.school,
            )
        else:
            schedules = Schedule.objects.filter(
                school=request.school,
            )
        serializer = ScheduleSerializer(schedules, many=True)

        response = {
            "response": serializer.data
        }

        return make_success_json_response(200, response_body=response)

    if request.method == "POST":
        try:
            request_body = json.loads(request.body)
            class_id = request_body.get("classId", "")
            day_name = request_body.get("day", "")
            class_time_str = request_body.get("classTime", "")

            if not class_id or not day_name or not class_time_str:
                return make_error_json_response("Missing required fields", 400)

            try:
                class_model = ClassModel.objects.get(
                    id=class_id,
                    school=request.school,
                )
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
                saved_schedule = serializer.save(school=request.school)
            else:
                return make_error_json_response(serializer.errors, 400)

            response = ScheduleSerializer.dict_to_camel_case({
                "message": "Schedule was created successfully",
                "schedule_id": saved_schedule.id,
                "class_id": saved_schedule.class_model.id,
                "class_name": saved_schedule.class_model.name,
                "day": saved_schedule.day.name,
                "time": saved_schedule.class_time,
            })

            return make_success_json_response(200, response_body=response)

        except json.JSONDecodeError:
            return make_error_json_response("Invalid JSON", 400)
        except Exception:
            return make_error_json_response("An internal error occurred", 500)


@teacher_or_above
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
            return make_error_json_response(
                "Class duration must be positive", 400)
    except ValueError:
        return make_error_json_response("Invalid duration_minutes format", 400)

    try:
        day_obj = Day.objects.get(name__iexact=day_param.strip())
    except Exception:
        return make_error_json_response(f"Day {day_param} does not exist", 400)

    schedules = Schedule.objects.filter(
        day=day_obj,
        school=request.school,
    )

    available_slots = calculate_available_time_slots(
        schedules, duration_minutes)

    response = CaseSerializer.dict_to_camel_case({
        "message": "Available time slots",
        "available_slots": available_slots,
    })

    return make_success_json_response(200, response_body=response)


def calculate_available_time_slots(
        schedules,
        duration_to_fit,
        step_minutes=None,
        day_start=None,
        day_end=None):
    if step_minutes is None:
        step_minutes = DEFAULT_TIME_SLOT_STEP_MINUTES
    if day_start is None:
        day_start = DEFAULT_DAY_START_TIME
    if day_end is None:
        day_end = DEFAULT_DAY_END_TIME
    available_slots, taken_slots = [], []
    base_date = datetime.today().date()

    dummy_day_start_class = datetime.combine(
        base_date, datetime.strptime(
            day_start, "%H:%M").time())
    dummy_day_end_class = datetime.combine(
        base_date, datetime.strptime(
            day_end, "%H:%M").time())
    taken_slots.append({"start_time": dummy_day_start_class,
                       "end_time": dummy_day_start_class})

    for schedule in schedules:
        start_time = datetime.combine(base_date, schedule.class_time)
        class_duration = schedule.class_model.duration_minutes
        end_time = start_time + timedelta(minutes=class_duration)
        taken_slots.append({"start_time": start_time, "end_time": end_time})

    taken_slots.append({"start_time": dummy_day_end_class,
                       "end_time": dummy_day_end_class})

    len_taken_slots = len(taken_slots)

    taken_slots = sorted(taken_slots, key=lambda x: x["start_time"])

    for i in range(len_taken_slots - 1):
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
                available_slots.append(
                    candidate_start.time().strftime("%H:%M"))
                candidate_start += step

    return available_slots

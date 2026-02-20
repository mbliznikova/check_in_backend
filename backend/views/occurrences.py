import json

from backend.decorators import kiosk_or_above, teacher_or_above
from django.db.models import Q
from django.http import JsonResponse
from django.utils.dateparse import parse_date, parse_time
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from backend.models import ClassModel, ClassOccurrence, Schedule
from backend.serializers import ClassOccurrenceSerializer, ClassModelSerializer
from backend.views.helpers import make_error_json_response, make_success_json_response


@kiosk_or_above
@csrf_exempt
@require_http_methods(["GET", "POST"])
def class_occurrences(request):
    if request.method == "GET":
        class_id = request.GET.get("class_id")
        if class_id:
            occurrences = ClassOccurrence.objects.filter(
                class_model=class_id,
                school=request.school,
            )
        else:
            occurrences = ClassOccurrence.objects.filter(
                school=request.school,
            )
        serializer = ClassOccurrenceSerializer(occurrences, many=True)

        response = {
            "response": serializer.data
        }

        return make_success_json_response(200, response_body=response)

    if request.method == "POST":
        try:
            request_body = json.loads(request.body)

            class_model_id = request_body.get("classModel")
            fallback_class_name = request_body.get("fallbackClassName", "")
            schedule_id = request_body.get("schedule")
            planned_date_str = request_body.get("plannedDate")
            planned_start_time_str = request_body.get("plannedStartTime")
            planned_duration = request_body.get("plannedDuration")
            notes = request_body.get("notes", "")

            if not planned_date_str or not planned_start_time_str:
                return make_error_json_response("plannedDate and plannedStartTime are required.", 400)

            planned_date = parse_date(planned_date_str)
            planned_start_time = parse_time(planned_start_time_str)
            if not planned_date:
                return make_error_json_response("Invalid date format", 400)
            if not planned_start_time:
                return make_error_json_response("Invalid time format", 400)

            class_model, schedule = None, None
            if class_model_id:
                class_model = ClassModel.objects.filter(id=class_model_id).first()
                if class_model is None:
                    return make_error_json_response(f"ClassModel {class_model_id} not found.", 404)
            if schedule_id:
                schedule = Schedule.objects.filter(id=schedule_id).first()
                if schedule is None:
                    return make_error_json_response(f"Schedule {schedule_id} not found.", 404)

            if not fallback_class_name and not class_model:
                fallback_class_name = "No name class"

            data_to_write = {
                "class_model": class_model.id if class_model else None,
                "fallback_class_name": fallback_class_name or None,
                "schedule": schedule.id if schedule else None,
                "planned_date": planned_date,
                "actual_date": planned_date,
                "planned_start_time": planned_start_time,
                "actual_start_time": planned_start_time,
                "planned_duration": planned_duration or 60,
                "actual_duration": planned_duration or 60,
                "notes": notes,
            }

            serializer = ClassOccurrenceSerializer(data=data_to_write)
            if serializer.is_valid():
                saved_occurrence = serializer.save(school=request.school)
            else:
                return make_error_json_response(serializer.errors, 400)

            response = ClassOccurrenceSerializer.dict_to_camel_case({
                "message": "Class occurrence was created successfully",
                "occurrence_id": saved_occurrence.id,
                "class_id": saved_occurrence.safe_class_id,
                "fallback_class_name": saved_occurrence.fallback_class_name,
                "planned_date": saved_occurrence.planned_date,
                "planned_start_time": saved_occurrence.planned_start_time,
                "planned_duration": saved_occurrence.planned_duration,
                "notes": saved_occurrence.notes,
            })

            return make_success_json_response(200, response_body=response)

        except json.JSONDecodeError:
            return make_error_json_response("Invalid JSON", 400)
        except Exception as e:
            return make_error_json_response("An internal error occurred", 500)


@teacher_or_above
@csrf_exempt
@require_http_methods(["PATCH"])
def edit_occurrence(request, occurrence_id):
    if request.method == "PATCH":
        try:
            occurrence_instance = ClassOccurrence.objects.get(
                id=occurrence_id,
                school=request.school,
            )

            request_body = json.loads(request.body)
            actual_date_str = request_body.get("actualDate")
            actual_start_time_str = request_body.get("actualStartTime")
            actual_duration_str = request_body.get("actualDuration")
            is_cancelled = request_body.get("isCancelled")
            notes = request_body.get("notes")

            data_to_write = {}

            if actual_date_str is not None:
                actual_date = parse_date(actual_date_str)
                if not actual_date:
                    return make_error_json_response(f"Invalid date format: {actual_date_str}", 400)

                data_to_write["actual_date"] = actual_date

            if actual_start_time_str is not None:
                actual_start_time = parse_time(actual_start_time_str)
                if not actual_start_time:
                    return make_error_json_response(f"Invalid time format: {actual_start_time_str}", 400)

                data_to_write["actual_start_time"] = actual_start_time

            if actual_duration_str is not None:
                try:
                    actual_duration = int(actual_duration_str)
                except ValueError as e:
                    return make_error_json_response(f"Invalid minutes value: {actual_duration_str}. Can not convert to int: {e}", 400)

                data_to_write["actual_duration"] = actual_duration

            if is_cancelled is not None:
                data_to_write["is_cancelled"] = is_cancelled

            if notes is not None:
                data_to_write["notes"] = notes

            serializer = ClassOccurrenceSerializer(occurrence_instance, data=data_to_write, partial=True)
            if serializer.is_valid():
                serializer.save(school=request.school)
            else:
                return make_error_json_response(serializer.errors, 400)

            response = ClassModelSerializer.dict_to_camel_case({
                "message": "Class Occurrence was updated successfully",
                "id": occurrence_id,
                **data_to_write,
            })

            return make_success_json_response(200, response_body=response)

        except ClassOccurrence.DoesNotExist:
            return make_error_json_response("Class occurrence not found", 404)
        except json.JSONDecodeError:
            return make_error_json_response("Invalid JSON", 400)
        except Exception as e:
            return make_error_json_response("An internal error occurred", 500)


@teacher_or_above
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_occurrence(request, occurrence_id):
    if request.method == "DELETE":
        try:
            occurrence_instance = ClassOccurrence.objects.get(
                id=occurrence_id,
                school=request.school,
            )
            occurrence_instance_id = occurrence_instance.id
            class_name = occurrence_instance.safe_class_name
            class_actual_date = occurrence_instance.actual_date
            class_actual_time = occurrence_instance.actual_start_time

            occurrence_instance.delete()

            response = ClassModelSerializer.dict_to_camel_case({
                "message": f"Occurrence for {class_name} at {class_actual_date} {class_actual_time} was deleted successfully",
                "occurrence_id": occurrence_instance_id,
            })

            return make_success_json_response(200, response_body=response)

        except ClassOccurrence.DoesNotExist:
            return make_error_json_response("Class Occurrence not found", 404)
        except Exception as e:
            return make_error_json_response("An internal error occurred", 500)


@kiosk_or_above
def today_class_occurrences(request):
    from datetime import date

    today_day = date.today()
    occurrences = ClassOccurrence.objects.filter(
        school=request.school,
    ).filter(
        Q(planned_date=today_day) | Q(actual_date=today_day)
    )

    serializer = ClassOccurrenceSerializer(occurrences, many=True)

    response = {
        "response": serializer.data
    }

    return make_success_json_response(200, response_body=response)

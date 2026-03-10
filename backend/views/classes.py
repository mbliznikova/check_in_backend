import json
from datetime import datetime

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from backend.decorators import teacher_or_above
from backend.models import ClassModel, Day, Schedule
from backend.serializers import ClassModelSerializer
from backend.views.helpers import (
    make_error_json_response, make_success_json_response,
)


@teacher_or_above
@csrf_exempt
@require_http_methods(["GET", "POST"])
def classes(request):
    if request.method == "GET":
        classes = ClassModel.objects.filter(school=request.school)
        serializer = ClassModelSerializer(classes, many=True)

        response = {
            "response": serializer.data
        }

        return make_success_json_response(200, response_body=response)

    if request.method == "POST":
        try:
            request_body = json.loads(request.body)
            name = request_body.get("name", "")
            duration_minutes = request_body.get("durationMinutes")
            is_recurring = request_body.get("isRecurring")

            if not name:
                return make_error_json_response(
                    "Class name should not be empty", 400)

            data_to_write = {
                "name": name
            }

            if duration_minutes is not None:
                data_to_write["duration_minutes"] = duration_minutes

            if is_recurring is not None:
                data_to_write["is_recurring"] = is_recurring

            serializer = ClassModelSerializer(data=data_to_write)
            if serializer.is_valid():
                saved_class = serializer.save(school=request.school)
            else:
                return make_error_json_response(serializer.errors, 400)

            response = ClassModelSerializer.dict_to_camel_case({
                "message": "Class was created successfully",
                "id": saved_class.id,
                "name": saved_class.name,
                "duration_minutes": saved_class.duration_minutes,
                "is_recurring": saved_class.is_recurring,
            })

            return make_success_json_response(200, response_body=response)

        except json.JSONDecodeError:
            return make_error_json_response("Invalid JSON", 400)
        except Exception:
            return make_error_json_response("An internal error occurred", 500)


@teacher_or_above
@csrf_exempt
@require_http_methods(["PUT"])
def edit_class(request, class_id):
    if request.method == "PUT":
        try:
            class_instance = ClassModel.objects.get(
                id=class_id,
                school=request.school,
            )

            request_body = json.loads(request.body)
            class_name = request_body.get("name")
            duration_minutes = request_body.get("durationMinutes")
            is_recurring = request_body.get("isRecurring")

            if class_name is not None:
                if not class_name.strip():
                    return make_error_json_response(
                        "Class name cannot be empty", 400)
                class_instance.name = class_name

            if duration_minutes is not None:
                class_instance.duration_minutes = duration_minutes

            if is_recurring is not None and is_recurring != class_instance.is_recurring:
                class_instance.is_recurring = is_recurring

            class_instance.save()

            response = ClassModelSerializer.dict_to_camel_case({
                "message": "Class was updated successfully",
                "class_id": class_instance.id,
                "class_name": class_instance.name,
                "duration_minutes": class_instance.duration_minutes,
                "is_recurring": class_instance.is_recurring,
            })

            return make_success_json_response(200, response_body=response)

        except ClassModel.DoesNotExist:
            return make_error_json_response("Class not found", 404)
        except json.JSONDecodeError:
            return make_error_json_response("Invalid JSON", 400)
        except Exception:
            return make_error_json_response("An internal error occurred", 500)


@teacher_or_above
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_class(request, class_id):
    if request.method == "DELETE":
        try:
            class_instance = ClassModel.objects.get(
                id=class_id,
                school=request.school,
            )
            class_instance_id = class_instance.id
            class_instance_name = class_instance.name

            class_instance.delete()

            response = ClassModelSerializer.dict_to_camel_case({
                "message": f"Class {class_instance_id} - {class_instance_name} was deleted successfully",
                "class_id": class_instance_id,
                "class_name": class_instance_name,
            })

            return make_success_json_response(200, response_body=response)

        except ClassModel.DoesNotExist:
            return make_error_json_response("Class not found", 404)
        except Exception:
            return make_error_json_response("An internal error occurred", 500)


def today_classes_list(request):
    today_name = datetime.today().strftime("%A")

    today_day_object = Day.objects.filter(name=today_name).first()
    if not today_day_object:
        return make_success_json_response(200, response_body={"response": []})

    scheduled_today = Schedule.objects.filter(
        school=request.school,
        day=today_day_object
    ).values("class_model")

    classes = ClassModel.objects.filter(
        id__in=scheduled_today,
        school=request.school,
    )

    serializer = ClassModelSerializer(classes, many=True)

    response = {
        "response": serializer.data
    }

    return make_success_json_response(200, response_body=response)

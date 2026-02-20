import json

from backend.decorators import kiosk_or_above, teacher_or_above
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from backend.models import Student
from backend.serializers import StudentSerializer
from backend.views.helpers import make_error_json_response, make_success_json_response


@csrf_exempt
@require_http_methods(["GET", "POST"])
def students_view(request):
    if request.method == "GET":
        return list_students(request)
    if request.method == "POST":
        return create_student(request)


@csrf_exempt
@kiosk_or_above
@require_http_methods(["GET"])
def list_students(request):
    students = Student.objects.filter(
        school=request.school,
    )
    serializer = StudentSerializer(students, many=True)

    response = {
        "response": serializer.data
    }

    return make_success_json_response(200, response_body=response)


@csrf_exempt
@teacher_or_above
@require_http_methods(["POST"])
def create_student(request):
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
            saved_student = serializer.save(school=request.school)
        else:
            return make_error_json_response(serializer.errors, 400)

        response = StudentSerializer.dict_to_camel_case({
            "message": "Student was created successfully",
            "student_id": saved_student.id,
            "first_name": saved_student.first_name,
            "last_name": saved_student.last_name,
            "is_liability_form_sent": saved_student.is_liability_form_sent,
            "emergency_contacts": saved_student.emergency_contacts,
        })

        return make_success_json_response(200, response_body=response)

    except json.JSONDecodeError:
        return make_error_json_response("Invalid JSON", 400)
    except Exception as e:
        return make_error_json_response("An internal error occurred", 500)


@teacher_or_above
@csrf_exempt
@require_http_methods(["PUT"])
def edit_student(request, student_id):
    if request.method == "PUT":
        try:
            student_instance = Student.objects.get(
                id=student_id,
                school=request.school,
            )

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

            response = StudentSerializer.dict_to_camel_case({
                "message": f"Student {student_instance.id} was updated successfully",
                "student_id": student_instance.id,
                "first_name": student_instance.first_name,
                "last_name": student_instance.last_name,
                "is_liability_form_sent": student_instance.is_liability_form_sent,
                "emergency_contacts": student_instance.emergency_contacts,
            })

            return make_success_json_response(200, response_body=response)

        except Student.DoesNotExist:
            return make_error_json_response("Student not found", 404)
        except json.JSONDecodeError:
            return make_error_json_response("Invalid JSON", 400)
        except Exception as e:
            return make_error_json_response("An internal error occurred", 500)


@teacher_or_above
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_student(request, student_id):
    if request.method == "DELETE":
        try:
            student_instance = Student.objects.get(
                id=student_id,
                school=request.school,
            )
            student_instance_id = student_instance.id

            student_instance.delete()

            response = StudentSerializer.dict_to_camel_case({
                "message": f"Student {student_instance_id} was deleted successfully",
                "student_id": student_instance_id,
            })

            return make_success_json_response(200, response_body=response)

        except Student.DoesNotExist:
            return make_error_json_response("Student not found", 404)
        except Exception as e:
            return make_error_json_response("An internal error occurred", 500)

import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from backend.decorators import admin_or_owner, any_authenticated_user
from backend.models import School, SchoolMembership
from backend.serializers import SchoolSerializer
from backend.views.helpers import (
    make_error_json_response, make_success_json_response,
)


@any_authenticated_user
@csrf_exempt
@require_http_methods(["GET", "POST"])
def schools(request):
    if request.method == "GET":
        try:
            memberships = SchoolMembership.objects.filter(
                user=request.user).select_related('school')
            schools_list = [membership.school for membership in memberships]
            serializer = SchoolSerializer(schools_list, many=True)
            response = {
                "response": serializer.data
            }
            return JsonResponse(response)
        except Exception:
            return make_error_json_response("An internal error occurred", 500)

    elif request.method == "POST":
        try:
            request_body = json.loads(request.body)
            name = request_body.get("name")
            clerk_org_id = request_body.get("clerkOrgId")
            phone = request_body.get("phone", "")
            address = request_body.get("address", "")
            logo_url = request_body.get("logoUrl", "")

            if not name or not clerk_org_id:
                return make_error_json_response(
                    "Name and clerkOrgId are required", 400)

            if School.objects.filter(clerk_org_id=clerk_org_id).exists():
                return make_error_json_response(
                    "School with this clerk organization ID already exists", 400)

            school = School.objects.create(
                name=name,
                clerk_org_id=clerk_org_id,
                phone=phone,
                address=address,
                logo_url=logo_url
            )

            SchoolMembership.objects.create(
                user=request.user,
                school=school,
                role="owner"
            )

            serializer = SchoolSerializer(school)
            response = {
                "message": "School created successfully",
                **serializer.data
            }
            return make_success_json_response(201, response_body=response)

        except json.JSONDecodeError:
            return make_error_json_response("Invalid JSON", 400)
        except Exception:
            return make_error_json_response("An internal error occurred", 500)


@admin_or_owner
@csrf_exempt
@require_http_methods(["GET"])
def school_detail(request, school_id):
    try:
        school = School.objects.get(id=school_id)
        serializer = SchoolSerializer(school)
        response = {
            "response": serializer.data
        }
        return JsonResponse(response)
    except School.DoesNotExist:
        return make_error_json_response("School not found", 404)
    except Exception:
        return make_error_json_response("An internal error occurred", 500)


@admin_or_owner
@csrf_exempt
@require_http_methods(["PATCH"])
def edit_school(request, school_id):
    try:
        school = School.objects.get(id=school_id)

        request_body = json.loads(request.body)
        name = request_body.get("name")
        phone = request_body.get("phone")
        address = request_body.get("address")
        logo_url = request_body.get("logoUrl")

        data_to_write = {}
        if name is not None:
            if not name.strip():
                return make_error_json_response(
                    "School name cannot be empty", 400)
            data_to_write["name"] = name
        if phone is not None:
            data_to_write["phone"] = phone
        if address is not None:
            data_to_write["address"] = address
        if logo_url is not None:
            data_to_write["logo_url"] = logo_url

        if not data_to_write:
            return make_error_json_response("No fields to update", 400)

        serializer = SchoolSerializer(school, data=data_to_write, partial=True)
        if serializer.is_valid():
            serializer.save()
        else:
            return make_error_json_response(serializer.errors, 400)

        response = {
            "message": "School was updated successfully",
            "school_id": school.id,
            **serializer.data,
        }
        return make_success_json_response(200, response_body=response)

    except School.DoesNotExist:
        return make_error_json_response("School not found", 404)
    except json.JSONDecodeError:
        return make_error_json_response("Invalid JSON", 400)
    except Exception:
        return make_error_json_response("An internal error occurred", 500)


@admin_or_owner
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_school(request, school_id):
    try:
        school = School.objects.get(id=school_id)
        school_id_val = school.id
        school_name = school.name

        school.delete()

        response = SchoolSerializer.dict_to_camel_case({
            "message": f"School {school_name} was deleted successfully",
            "school_id": school_id_val,
        })
        return make_success_json_response(200, response_body=response)

    except School.DoesNotExist:
        return make_error_json_response("School not found", 404)
    except Exception:
        return make_error_json_response("An internal error occurred", 500)

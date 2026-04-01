import json
import logging

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from ..decorators import admin_or_owner
from ..models import SchoolMembership
from ..serializers import MembershipSerializer
from .helpers import make_error_json_response, make_success_json_response

logger = logging.getLogger(__name__)


@admin_or_owner
@csrf_exempt
@require_http_methods(["GET"])
def list_memberships(request):
    memberships = SchoolMembership.objects.filter(
        school=request.school
    ).select_related("user")
    members = [
        MembershipSerializer.dict_to_camel_case({
            "id": m.id,
            "first_name": m.user.first_name,
            "last_name": m.user.last_name,
            "email": m.user.email,
            "role": m.role,
        })
        for m in memberships
    ]
    return make_success_json_response(200, response_body={"members": members})


@admin_or_owner
@csrf_exempt
@require_http_methods(["PATCH"])
def edit_membership(request, membership_id):
    try:
        membership = SchoolMembership.objects.select_related("user").get(
            id=membership_id,
            school=request.school,
        )

        request_body = json.loads(request.body)
        new_role = request_body.get("role")

        if new_role is None:
            return make_error_json_response("role is required", 400)

        valid_roles = [choice[0] for choice in SchoolMembership.ROLE_CHOICES]
        if new_role not in valid_roles:
            return make_error_json_response(
                f"Invalid role. Valid choices: {', '.join(valid_roles)}", 400
            )

        if membership.role == "owner" and new_role != "owner":
            owner_count = SchoolMembership.objects.filter(
                school=request.school, role="owner"
            ).count()
            if owner_count <= 1:
                return make_error_json_response(
                    "Cannot change role of the last owner", 400
                )

        membership.role = new_role
        membership.save(update_fields=["role"])

        response = MembershipSerializer.dict_to_camel_case({
            "message": f"Membership {membership.id} was updated successfully",
            "membership_id": membership.id,
            "role": membership.role,
        })
        return make_success_json_response(200, response_body=response)

    except SchoolMembership.DoesNotExist:
        return make_error_json_response("Membership not found", 404)
    except json.JSONDecodeError:
        return make_error_json_response("Invalid JSON", 400)
    except Exception:
        logger.exception("edit_membership: unexpected error membership_id=%s", membership_id)
        return make_error_json_response("An internal error occurred", 500)


@admin_or_owner
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_membership(request, membership_id):
    try:
        membership = SchoolMembership.objects.get(
            id=membership_id,
            school=request.school,
        )

        if membership.role == "owner":
            owner_count = SchoolMembership.objects.filter(
                school=request.school, role="owner"
            ).count()
            if owner_count <= 1:
                return make_error_json_response(
                    "Cannot remove the last owner of a school", 400
                )

        membership_id_val = membership.id
        membership.delete()

        response = MembershipSerializer.dict_to_camel_case({
            "message": f"Membership {membership_id_val} was deleted successfully",
            "membership_id": membership_id_val,
        })
        return make_success_json_response(200, response_body=response)

    except SchoolMembership.DoesNotExist:
        return make_error_json_response("Membership not found", 404)
    except Exception:
        logger.exception("delete_membership: unexpected error membership_id=%s", membership_id)
        return make_error_json_response("An internal error occurred", 500)

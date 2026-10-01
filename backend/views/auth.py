import logging

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from backend.decorators import any_authenticated_user, clerk_claims_required
from backend.models import SchoolMembership
from backend.serializers import CaseSerializer
from backend.services.user_sync import EmailConflict, provision_clerk_user
from backend.views.helpers import (
    make_error_json_response, make_success_json_response,
)

logger = logging.getLogger(__name__)


@any_authenticated_user
def get_user(request):
    memberships = SchoolMembership.objects.select_related("school").filter(
        user=request.user
    )

    response = {
        "user_id": request.user.id,
        "memberships": [
            CaseSerializer.dict_to_camel_case({
                "school_id": m.school.id,
                "school_name": m.school.name,
                "role": m.role,
            })
            for m in memberships
        ],
    }

    response = CaseSerializer.dict_to_camel_case(response)

    return make_success_json_response(200, response_body=response)


@clerk_claims_required
@csrf_exempt
@require_http_methods(["POST"])
def provision_user(request):
    claims = request.clerk_claims
    clerk_user_id = claims.get("sub")
    email = claims.get("email")

    if not clerk_user_id or not email:
        return make_error_json_response("Missing required token claims", 400)

    extra_fields = {k: v for k, v in {
        "first_name": claims.get("first_name"),
        "last_name": claims.get("last_name"),
    }.items() if v is not None}

    try:
        user = provision_clerk_user(
            clerk_user_id, email, claims.get("email_verified", False), extra_fields)
    except EmailConflict:
        return make_error_json_response(
            "An account with this email already exists; verify your email to link accounts", 409)
    except Exception:
        logger.exception("provision_user: failed for clerk_user_id=%s", clerk_user_id)
        return make_error_json_response("An internal error occurred", 500)

    memberships = SchoolMembership.objects.select_related("school").filter(user=user)

    response = {
        "user_id": user.id,
        "memberships": [
            CaseSerializer.dict_to_camel_case({
                "school_id": m.school.id,
                "school_name": m.school.name,
                "role": m.role,
            })
            for m in memberships
        ],
    }

    response = CaseSerializer.dict_to_camel_case(response)

    return make_success_json_response(200, response_body=response)

import logging

from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from backend.decorators import any_authenticated_user, clerk_claims_required
from backend.models import School, SchoolMembership
from backend.serializers import CaseSerializer
from backend.services.clerk_client import ClerkDeleteError, delete_clerk_user
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


@any_authenticated_user
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_account(request):
    user = request.user

    if SchoolMembership.objects.filter(user=user, role="kiosk").exists():
        return make_error_json_response("Kiosk accounts cannot self-delete", 403)

    clerk_user_id = user.clerk_user_id
    user_id = user.id

    try:
        with transaction.atomic():
            owner_school_ids = list(
                SchoolMembership.objects.filter(user=user, role="owner")
                .values_list("school_id", flat=True)
            )

            # select_for_update: the count-then-cascade check is otherwise a
            # check-then-act race — two co-owners of the same school deleting
            # concurrently could each see count()==2, both skip the cascade,
            # and leave the school with zero owners. Locking each candidate
            # school's owner rows for the duration of this transaction forces
            # the second deleter to re-read a fresh count after the first
            # commits, so the correct final deleter cascades it instead.
            sole_owned_school_ids = []
            for sid in owner_school_ids:
                owner_membership_count = (
                    SchoolMembership.objects.select_for_update()
                    .filter(school_id=sid, role="owner")
                    .count()
                )
                if owner_membership_count == 1:
                    sole_owned_school_ids.append(sid)

            cascaded_org_ids = list(
                School.objects.filter(id__in=sole_owned_school_ids)
                .values_list("clerk_org_id", flat=True)
            )

            School.objects.filter(id__in=sole_owned_school_ids).delete()
            SchoolMembership.objects.filter(user=user).delete()
            user.delete()
    except Exception:
        logger.exception("delete_account: local cascade failed for user_id=%s", user_id)
        return make_error_json_response("An internal error occurred", 500)

    if cascaded_org_ids:
        logger.info(
            "delete_account: cascaded schools with clerk_org_id=%s for user_id=%s "
            "(Clerk org cleanup not automated)",
            cascaded_org_ids, user_id,
        )

    try:
        delete_clerk_user(clerk_user_id)
    except ClerkDeleteError:
        logger.error(
            "delete_account: local data for user_id=%s deleted, but Clerk user "
            "clerk_user_id=%s could not be deleted after retries — needs manual cleanup",
            user_id, clerk_user_id,
        )
        return make_error_json_response(
            "Account data was deleted, but your sign-in identity could not be "
            "fully removed. Contact support.", 502,
        )

    response = {"message": "Account deleted successfully", "userId": user_id}
    return make_success_json_response(200, response_body=response)

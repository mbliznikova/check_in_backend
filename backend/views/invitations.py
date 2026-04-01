import json
import logging
from datetime import datetime, timedelta

from django.http import JsonResponse
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from backend.decorators import admin_or_owner, any_authenticated_user
from backend.models import Invitation, SchoolMembership
from backend.serializers import CaseSerializer, InvitationSerializer
from backend.views.helpers import (
    make_error_json_response, make_success_json_response,
)

logger = logging.getLogger(__name__)

@admin_or_owner
@csrf_exempt
@require_http_methods(["POST"])
def create_invitation(request):
    logger.info(
        "create_invitation called by user=%s school=%s",
        request.user.id, getattr(request.school, "id", None)
    )
    try:
        request_body = json.loads(request.body)

        email = request_body.get("email")
        role = request_body.get("role")

        if not email or not role:
            logger.warning("create_invitation: missing email or role")
            return make_error_json_response("Email and role are required", 400)

        valid_roles = [choice[0] for choice in SchoolMembership.ROLE_CHOICES]
        if role not in valid_roles:
            logger.warning("create_invitation: invalid role=%s", role)
            return make_error_json_response("Invalid role", 400)

        if SchoolMembership.objects.filter(
            school=request.school,
            user__email__iexact=email
        ).exists():
            logger.info("create_invitation: email=%s is already a member of school=%s", email, request.school.id)
            return make_error_json_response(
                "User is already a member of this school", 400
            )

        if Invitation.objects.filter(
            school=request.school,
            email__iexact=email,
            accepted=False
        ).exists():
            logger.info("create_invitation: active invitation already exists for email=%s school=%s", email, request.school.id)
            return make_error_json_response(
                "An active invitation already exists for this email", 400
            )

        invitation = Invitation.objects.create(
            school=request.school,
            email=email,
            role=role,
            invited_by=request.user,
            expires_at=now() + timedelta(days=7)
        )
        logger.info("create_invitation: created invitation id=%s for email=%s role=%s school=%s", invitation.id, email, role, request.school.id)

        # TODO: make a constant, change address when needed. Now it's for test.
        # TODO: use uuid?
        invite_link = f"http://localhost:8081/invite/{invitation.id}"

        serializer = InvitationSerializer(invitation)
        response = InvitationSerializer.dict_to_camel_case({
            "message": "Invitation created successfully",
            **serializer.data,
            "invite_link": invite_link,
        })

        return make_success_json_response(201, response_body=response)

    except json.JSONDecodeError:
        logger.warning("create_invitation: invalid JSON body")
        return make_error_json_response("Invalid JSON", 400)
    except Exception:
        logger.exception("create_invitation: unexpected error for user=%s school=%s", request.user.id, getattr(request.school, "id", None))
        return make_error_json_response("An internal error occurred", 500)

@any_authenticated_user
@csrf_exempt
@require_http_methods(["POST"])
def accept_invitation(request, invitation_id):
    logger.info("accept_invitation called by user=%s invitation_id=%s", request.user.id, invitation_id)
    try:
        invitation = Invitation.objects.select_related("school").get(id=invitation_id)

        if invitation.accepted:
            logger.info("accept_invitation: invitation id=%s already accepted", invitation_id)
            return make_error_json_response("Invitation already accepted", 400)

        if not invitation.is_valid():
            logger.info("accept_invitation: invitation id=%s has expired", invitation_id)
            return make_error_json_response("Invitation expired", 400)

        if not request.user.email or invitation.email.lower() != request.user.email.lower():
            logger.warning(
                "accept_invitation: email mismatch — invitation email=%s user email=%s",
                invitation.email, request.user.email
            )
            return make_error_json_response("This invitation is not for this user", 403)

        if SchoolMembership.objects.filter(
            user=request.user,
            school=invitation.school
        ).exists():
            logger.info("accept_invitation: user=%s is already a member of school=%s", request.user.id, invitation.school.id)
            return make_error_json_response("Already a member of this school", 400)

        SchoolMembership.objects.create(
            user=request.user,
            school=invitation.school,
            role=invitation.role
        )

        invitation.accepted = True
        invitation.save(update_fields=["accepted"])
        logger.info("accept_invitation: user=%s joined school=%s with role=%s", request.user.id, invitation.school.id, invitation.role)

        response = CaseSerializer.dict_to_camel_case({
            "message": "Invitation accepted successfully",
            "school_id": invitation.school.id,
            "school_name": invitation.school.name,
            "role": invitation.role,
        })

        return make_success_json_response(200, response_body=response)

    except Invitation.DoesNotExist:
        logger.warning("accept_invitation: invitation id=%s not found", invitation_id)
        return make_error_json_response("Invitation not found", 404)
    except Exception:
        logger.exception("accept_invitation: unexpected error for user=%s invitation_id=%s", request.user.id, invitation_id)
        return make_error_json_response("An internal error occurred", 500)

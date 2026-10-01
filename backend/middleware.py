import logging

import jwt
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.utils.functional import SimpleLazyObject

from .models import SchoolMembership
from .services import verify_token

logger = logging.getLogger(__name__)

User = get_user_model()


def verify_clerk_claims(request):
    """Pure token verification — no DB access. Returns the token's claims
    (sub, email, normalized email_verified, first_name, last_name) or None
    if the request has no valid Clerk token."""
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ")[1]

    try:
        decoded = verify_token.verify_clerk_token(token)

        if not decoded:
            return None

        raw_email_verified = decoded.get("email_verified")

        return {
            "sub": decoded.get("sub"),
            "email": decoded.get("email"),
            "email_verified": raw_email_verified is True or raw_email_verified == "verified",
            "first_name": decoded.get("first_name"),
            "last_name": decoded.get("last_name"),
        }

    except jwt.ExpiredSignatureError as e:
        logger.warning(f"Expired Signature Error: {e}")
        return None

    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None

    except Exception as e:
        logger.exception("Unexpected Clerk auth error: %s", e)
        return None


def resolve_clerk_user(claims):
    """Read-only: resolves an existing User by clerk_user_id. Never creates,
    reattaches, or mutates a row — provisioning happens only via the
    explicit POST /backend/me/provision/ endpoint."""
    if not claims or not claims.get("sub"):
        return AnonymousUser()

    user = User.objects.filter(clerk_user_id=claims["sub"]).first()
    return user if user is not None else AnonymousUser()


# Paths that do not require school membership validation
EXEMPT_PATHS = {"/backend/me/", "/backend/me/provision/", "/backend/schools/"}


class ClerkAuthenticationMiddleware:
    """
    - Reads Clerk session token from Authorization header
    - Validates token using verify_token service (jwt), read-only
    - Attaches request.clerk_claims (always, even if no local User exists)
    - Resolves request.user by clerk_user_id only — never creates or mutates
      a User row; provisioning is a separate, explicit endpoint
    - Resolves school
    - Attaches request.school, request.role and request.membership
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/admin"):
            return self.get_response(request)

        claims = verify_clerk_claims(request)
        request.clerk_claims = claims
        request.user = SimpleLazyObject(lambda: resolve_clerk_user(claims))

        if request.path.startswith("/backend/invitations/") and request.path.endswith("/accept/"):
            return self.get_response(request)

        if request.path in EXEMPT_PATHS:
            return self.get_response(request)

        # TODO: revisit
        if not request.user or request.user.is_anonymous:
            return self.get_response(request)

        school_id = request.headers.get("X-School-ID")
        if not school_id:
            raise PermissionError("Missing X-School-ID header")

        try:
            membership = SchoolMembership.objects.select_related("school").get(
                user=request.user,
                school_id=school_id,
            )
        except SchoolMembership.DoesNotExist:
            raise PermissionDenied("You are not a member of this school")

        request.school = membership.school
        request.membership = membership
        request.role = membership.role

        return self.get_response(request)

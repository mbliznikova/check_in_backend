import os
import jwt
import logging

from django.utils.functional import SimpleLazyObject
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from .services import user_sync, verify_token

logger = logging.getLogger(__name__)

User = get_user_model()

def get_clerk_user(request):
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return AnonymousUser()

    token = auth_header.split(" ")[1]

    try:
        decoded = verify_token.verify_clerk_token(token)

        if not decoded:
            return AnonymousUser()

        clerk_user_id = decoded.get("sub")
        email = decoded.get("email")
        extra_fields = {
            "first_name": decoded.get("first_name"),
            "last_name": decoded.get("last_name"),
        }

        user = user_sync.sync_clerk_user(clerk_user_id, email, extra_fields)

        return user

    except jwt.ExpiredSignatureError as e:
        logger.warning(f"Expired Signature Error: {e}")
        return AnonymousUser()

    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return AnonymousUser()

    except Exception as e:
        logger.exception(f"Unexpected Clerk auth error: {e}")
        return AnonymousUser()

class ClerkAuthenticationMiddleware:
    """
    - Reads Clerk session token from Authorization header
    - Validates token using verify_token service (jwt)
    - Syncs Clerk user -> Django user model
    - Attaches request.user
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.user = SimpleLazyObject(lambda: get_clerk_user(request))
        return self.get_response(request)

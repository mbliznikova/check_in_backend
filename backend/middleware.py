import os
import jwt
import traceback

from dotenv import load_dotenv
from functools import wraps
from jwt import PyJWKClient

from django.http import JsonResponse
from django.utils.functional import SimpleLazyObject
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from clerk_backend_api import Clerk
from clerk_backend_api.models.sdkerror import SDKError

load_dotenv()

CLERK_SECRET_KEY = os.environ.get("CLERK_SECRET_KEY")
CLERK_JWKS_URL = os.environ.get("CLERK_JWKS_URL")
CLERK_ISSUER = os.environ.get("CLERK_ISSUER")
CLERK_AUDIENCE = os.environ.get("CLERK_AUDIENCE")

jwks_client = PyJWKClient(CLERK_JWKS_URL)
clerk_client = Clerk(CLERK_SECRET_KEY)

User = get_user_model()

def clerk_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user or request.user.is_anonymous:
            return JsonResponse({"error": "Unauthorized"}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper

def get_clerk_user(request):
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return AnonymousUser()

    token = auth_header.split(" ")[1]

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token).key

        decoded = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=CLERK_AUDIENCE,
            issuer=CLERK_ISSUER,
            options={"verify_aud": True},
        )

        clerk_user_id = decoded["sub"]

        try:
            user = User.objects.get(clerk_user_id=clerk_user_id)
        except User.DoesNotExist:
            email = decoded.get("email")

            user = User.objects.create(
                username=email,
                email=email,
                clerk_user_id=clerk_user_id,
                role="teacher",
            )

        return user

    except Exception as e:
        print("JWT VERIFICATION ERROR:", type(e), str(e))
        traceback.print_exc()
        return AnonymousUser()

class ClerkAuthenticationMiddleware:
    """
    - Reads Clerk session token from Authorization header
    - Validates token using clerk-sdk-python
    - Syncs Clerk user -> Django user model
    - Attaches request.user
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.user = SimpleLazyObject(lambda: get_clerk_user(request))
        return self.get_response(request)

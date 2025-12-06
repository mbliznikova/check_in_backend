from django.utils.functional import SimpleLazyObject
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.conf import settings

from clerk_backend_api import Clerk
from clerk_backend_api.models.sdkerror import SDKError

User = get_user_model()

clerk_client = Clerk(settings.CLERK_SECRET_KEY)

def get_clerk_user(request):
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return AnonymousUser()
    
    token = auth_header.split(" ")[1]

    try:
        session = clerk_client.sessions.verify(token)
        clerk_user_id = session.user_id

        # Try to find existing local user
        try:
            user = User.objects.get(clerk_user_id=clerk_user_id)
        except User.DoesNotExist:
            # Create user if not found (sync from Clerk)
            clerk_user = clerk_client.users.get(clerk_user_id)

            email = clerk_user.email_addresses[0].email_address

            user = User.objects.create(
                username=email,
                email=email,
                clerk_user_id=clerk_user_id,
                role="teacher",
            )

        return user

    except SDKError:
        return AnonymousUser()
    except Exception:
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

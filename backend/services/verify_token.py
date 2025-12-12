import os
import jwt
import logging

from dotenv import load_dotenv
from jwt import PyJWKClient

load_dotenv()

logger = logging.getLogger(__name__)

CLERK_ISSUER = os.environ.get("CLERK_ISSUER")
CLERK_AUDIENCE = os.environ.get("CLERK_AUDIENCE")
CLERK_JWKS_URL = os.environ.get("CLERK_JWKS_URL")

jwks_client = PyJWKClient(CLERK_JWKS_URL)

def verify_clerk_token(jwt_token):
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(jwt_token).key

        decoded_token = jwt.decode(
            jwt_token,
            signing_key,
            algorithms=["RS256"],
            audience=CLERK_AUDIENCE,
            issuer=CLERK_ISSUER,
            options={"verify_aud": True},
        )

        return decoded_token

    except Exception as e:
        logger.exception(f"Token verification failed: {e}")
        return None

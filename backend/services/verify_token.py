import logging
from functools import lru_cache

import jwt
from django.conf import settings
from jwt import PyJWKClient

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _jwks_client():
    return PyJWKClient(settings.CLERK_JWKS_URL)


def verify_clerk_token(jwt_token):
    try:
        signing_key = _jwks_client().get_signing_key_from_jwt(jwt_token).key

        decoded_token = jwt.decode(
            jwt_token,
            signing_key,
            algorithms=["RS256"],
            audience=settings.CLERK_AUDIENCE,
            issuer=settings.CLERK_ISSUER,
            options={"verify_aud": True},
        )

        return decoded_token

    except Exception as e:
        logger.exception(f"Token verification failed: {e}")
        return None

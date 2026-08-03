import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import transaction

logger = logging.getLogger(__name__)

User = get_user_model()


def _find_by_clerk_id(clerk_user_id):
    return User.objects.filter(clerk_user_id=clerk_user_id).first()


def _find_and_reattach_by_email(clerk_user_id, user_email):
    user = User.objects.filter(email=user_email).first()

    if user is None:
        return None

    old_clerk_user_id = user.clerk_user_id
    user.clerk_user_id = clerk_user_id
    user.save(update_fields=["clerk_user_id"])

    logger.info(
        "Reattached clerk_user_id for existing user email=%s: old_clerk_user_id=%s new_clerk_user_id=%s",
        user_email, old_clerk_user_id, clerk_user_id,
    )

    return user


def _create_user(clerk_user_id, user_email, extra_fields):
    return User.objects.create(
        clerk_user_id=clerk_user_id,
        email=user_email,
        username=user_email,
        **extra_fields
    )


def sync_clerk_user(clerk_user_id, user_email, extra_fields, email_verified=False):
    if not clerk_user_id or not user_email:
        logger.warning(
            "Cannot sync Clerk user: missing clerk_user_id=%s or user_email=%s",
            clerk_user_id, user_email,
        )
        return AnonymousUser()

    extra_fields = {k: v for k, v in (extra_fields or {}).items() if v is not None}

    try:
        with transaction.atomic():
            user = _find_by_clerk_id(clerk_user_id)

            if user is None and email_verified:
                user = _find_and_reattach_by_email(clerk_user_id, user_email)

            if user is None:
                user = _create_user(clerk_user_id, user_email, extra_fields)

        return user

    except Exception as e:
        logger.exception("Failed to sync Clerk user clerk_user_id=%s: %s", clerk_user_id, e)
        return AnonymousUser()

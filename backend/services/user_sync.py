import logging

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

logger = logging.getLogger(__name__)

User = get_user_model()


class EmailConflict(Exception):
    """Raised when a new, unverified Clerk identity's email already belongs
    to an existing account. The caller (view) turns this into a 409 instead
    of letting a DB IntegrityError on create get swallowed into a silent
    auth failure."""

    def __init__(self, email):
        self.email = email
        super().__init__(f"Email already associated with an existing account: {email}")


def _find_by_clerk_id(clerk_user_id):
    return User.objects.filter(clerk_user_id=clerk_user_id).first()


def _reattach(clerk_user_id, user):
    old_clerk_user_id = user.clerk_user_id
    user.clerk_user_id = clerk_user_id
    user.save(update_fields=["clerk_user_id"])

    logger.info(
        "Reattached clerk_user_id for existing user email=%s: old_clerk_user_id=%s new_clerk_user_id=%s",
        user.email, old_clerk_user_id, clerk_user_id,
    )

    return user


def _create_user(clerk_user_id, user_email, extra_fields):
    return User.objects.create(
        clerk_user_id=clerk_user_id,
        email=user_email,
        username=clerk_user_id,
        **extra_fields
    )


def provision_clerk_user(clerk_user_id, user_email, email_verified, extra_fields):
    extra_fields = {k: v for k, v in (extra_fields or {}).items() if v is not None}

    with transaction.atomic():
        user = _find_by_clerk_id(clerk_user_id)
        if user is not None:
            return user

        existing_by_email = User.objects.filter(email=user_email).first()
        if existing_by_email is not None:
            if not email_verified:
                raise EmailConflict(user_email)
            return _reattach(clerk_user_id, existing_by_email)

        try:
            return _create_user(clerk_user_id, user_email, extra_fields)
        except IntegrityError:
            # Race: another request provisioned the same clerk_user_id
            # concurrently between our lookup above and this create.
            user = _find_by_clerk_id(clerk_user_id)
            if user is None:
                raise
            return user

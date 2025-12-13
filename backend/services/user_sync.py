import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import transaction

logger = logging.getLogger(__name__)

User = get_user_model()

def sync_clerk_user(clerk_user_id, user_email, extra_fields):
    if not clerk_user_id or not user_email:
        return AnonymousUser()

    extra_fields = extra_fields or {}

    try:
        with transaction.atomic():
            user, _ = User.objects.get_or_create(
                clerk_user_id=clerk_user_id,
                defaults={
                    "email": user_email,
                    "username": user_email,
                    **extra_fields
                },
            )

        return user

    except Exception as e:
        logger.exception(f"Failed to sync Clerk user: {e}")
        return AnonymousUser()

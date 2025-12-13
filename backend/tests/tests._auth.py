from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from unittest.mock import patch

from backend.services.user_sync import sync_clerk_user

User = get_user_model()

class SyncClerkUserTests(TestCase):

    def test_creates_user_if_not_exists(self):
        clerk_user_id = "user_123"
        email = "test@example.com"

        user = sync_clerk_user(
            clerk_user_id=clerk_user_id,
            user_email=email,
            extra_fields=None
        )

        self.assertFalse(user.is_anonymous)
        self.assertEqual(user.clerk_user_id, clerk_user_id)
        self.assertEqual(user.email, email)

        self.assertEqual(User.objects.count(), 1)

    def test_returns_existing_user(self):
        clerk_user_id = "user_123"
        email = "test@example.com"

        existing_user = User.objects.create(
            clerk_user_id=clerk_user_id,
            email=email,
            username=email,
        )

        user = sync_clerk_user(
            clerk_user_id=clerk_user_id,
            user_email=email,
            extra_fields=None
        )

        self.assertEqual(user.id, existing_user.id)
        self.assertEqual(User.objects.count(), 1)

    def test_is_race_safe(self):
        clerk_user_id = "user_123"
        email = "test@example.com"

        user1 = sync_clerk_user(clerk_user_id, email, None)
        user2 = sync_clerk_user(clerk_user_id, email, None)

        self.assertEqual(user1.id, user2.id)
        self.assertEqual(User.objects.count(), 1)

    def test_returns_anonymous_on_invalid_input(self):
        user = sync_clerk_user(
            clerk_user_id=None,  # invalid, will break unique constraint
            user_email=None,
            extra_fields=None
        )

        self.assertIsInstance(user, AnonymousUser)
        self.assertEqual(User.objects.count(), 0)

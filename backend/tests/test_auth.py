from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

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

    def test_reattaches_clerk_id_on_verified_email_match(self):
        old_clerk_user_id = "user_old"
        new_clerk_user_id = "user_new"
        email = "test@example.com"

        existing_user = User.objects.create(
            clerk_user_id=old_clerk_user_id,
            email=email,
            username=email,
        )

        user = sync_clerk_user(
            clerk_user_id=new_clerk_user_id,
            user_email=email,
            extra_fields=None,
            email_verified=True,
        )

        self.assertEqual(user.id, existing_user.id)
        self.assertEqual(user.clerk_user_id, new_clerk_user_id)
        self.assertEqual(User.objects.count(), 1)

    def test_does_not_reattach_on_unverified_email_match(self):
        old_clerk_user_id = "user_old"
        new_clerk_user_id = "user_new"
        email = "test@example.com"

        User.objects.create(
            clerk_user_id=old_clerk_user_id,
            email=email,
            username=email,
        )

        user = sync_clerk_user(
            clerk_user_id=new_clerk_user_id,
            user_email=email,
            extra_fields=None,
            email_verified=False,
        )

        self.assertIsInstance(user, AnonymousUser)
        self.assertEqual(User.objects.count(), 1)

    def test_logs_info_on_reattachment(self):
        email = "test@example.com"

        User.objects.create(
            clerk_user_id="user_old",
            email=email,
            username=email,
        )

        with self.assertLogs("backend.services.user_sync", level="INFO") as cm:
            sync_clerk_user(
                clerk_user_id="user_new",
                user_email=email,
                extra_fields=None,
                email_verified=True,
            )

        self.assertTrue(any("Reattached clerk_user_id" in message for message in cm.output))

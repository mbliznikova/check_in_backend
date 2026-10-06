from django.contrib.auth import get_user_model
from django.test import TestCase

from backend.services.user_sync import EmailConflict, provision_clerk_user

User = get_user_model()


class ProvisionClerkUserTests(TestCase):

    def test_creates_user_if_not_exists(self):
        clerk_user_id = "user_123"
        email = "test@example.com"

        user = provision_clerk_user(
            clerk_user_id=clerk_user_id,
            user_email=email,
            email_verified=False,
            extra_fields=None,
        )

        self.assertEqual(user.clerk_user_id, clerk_user_id)
        self.assertEqual(user.email, email)
        self.assertEqual(user.username, clerk_user_id)
        self.assertEqual(User.objects.count(), 1)

    def test_returns_existing_user(self):
        clerk_user_id = "user_123"
        email = "test@example.com"

        existing_user = User.objects.create(
            clerk_user_id=clerk_user_id,
            email=email,
            username=clerk_user_id,
        )

        user = provision_clerk_user(
            clerk_user_id=clerk_user_id,
            user_email=email,
            email_verified=False,
            extra_fields=None,
        )

        self.assertEqual(user.id, existing_user.id)
        self.assertEqual(User.objects.count(), 1)

    def test_is_race_safe(self):
        clerk_user_id = "user_123"
        email = "test@example.com"

        user1 = provision_clerk_user(clerk_user_id, email, False, None)
        user2 = provision_clerk_user(clerk_user_id, email, False, None)

        self.assertEqual(user1.id, user2.id)
        self.assertEqual(User.objects.count(), 1)

    def test_links_clerk_id_on_verified_email_match(self):
        old_clerk_user_id = "user_old"
        new_clerk_user_id = "user_new"
        email = "test@example.com"

        existing_user = User.objects.create(
            clerk_user_id=old_clerk_user_id,
            email=email,
            username=old_clerk_user_id,
        )

        user = provision_clerk_user(
            clerk_user_id=new_clerk_user_id,
            user_email=email,
            email_verified=True,
            extra_fields=None,
        )

        self.assertEqual(user.id, existing_user.id)
        self.assertEqual(user.clerk_user_id, new_clerk_user_id)
        self.assertEqual(User.objects.count(), 1)

    def test_raises_email_conflict_on_unverified_email_match(self):
        old_clerk_user_id = "user_old"
        new_clerk_user_id = "user_new"
        email = "test@example.com"

        User.objects.create(
            clerk_user_id=old_clerk_user_id,
            email=email,
            username=old_clerk_user_id,
        )

        with self.assertRaises(EmailConflict):
            provision_clerk_user(
                clerk_user_id=new_clerk_user_id,
                user_email=email,
                email_verified=False,
                extra_fields=None,
            )

        # Nothing was created or mutated — the existing row is untouched.
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(
            User.objects.get(email=email).clerk_user_id, old_clerk_user_id)

    def test_logs_info_on_link(self):
        email = "test@example.com"

        User.objects.create(
            clerk_user_id="user_old",
            email=email,
            username="user_old",
        )

        with self.assertLogs("backend.services.user_sync", level="INFO") as cm:
            provision_clerk_user(
                clerk_user_id="user_new",
                user_email=email,
                email_verified=True,
                extra_fields=None,
            )

        self.assertTrue(any("Reattached clerk_user_id" in message for message in cm.output))

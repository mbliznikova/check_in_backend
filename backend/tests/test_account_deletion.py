"""Tests for DELETE /backend/me/delete/: cascade-only v1 account deletion.

Covers the sole-owner school cascade, the kiosk self-delete guard, and the
DB-first-then-Clerk-delete ordering (including that a failed local cascade
must never reach the Clerk API call).
"""
import json
from unittest.mock import Mock, patch

from django.test import TestCase

from backend.models import School, SchoolMembership, Student, User


class AccountDeletionTests(TestCase):

    def _mock_clerk_token(self, payload):
        return patch(
            "backend.middleware.verify_token.verify_clerk_token",
            return_value=payload,
        )

    def _mock_clerk_delete(self, **kwargs):
        return patch("backend.services.clerk_client.requests.delete", **kwargs)

    def _make_user(self, clerk_user_id, email):
        return User.objects.create(
            clerk_user_id=clerk_user_id, email=email, username=clerk_user_id,
        )

    def _make_school(self, name, clerk_org_id):
        return School.objects.create(name=name, clerk_org_id=clerk_org_id)

    def _delete_account(self, clerk_user_id, email="user@example.com"):
        payload = {"sub": clerk_user_id, "email": email, "email_verified": True}
        with self._mock_clerk_token(payload):
            return self.client.delete(
                "/backend/me/delete/", HTTP_AUTHORIZATION="Bearer test-token")

    def test_sole_owner_delete_cascades_school(self):
        user = self._make_user("user_owner", "owner@example.com")
        school = self._make_school("Sole School", "org_sole")
        SchoolMembership.objects.create(user=user, school=school, role="owner")
        Student.objects.create(school=school, first_name="A", last_name="B")

        with self._mock_clerk_delete(return_value=Mock(status_code=200)) as mock_delete:
            response = self._delete_account("user_owner")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 0)
        self.assertFalse(School.objects.filter(id=school.id).exists())
        self.assertFalse(Student.objects.filter(school_id=school.id).exists())
        self.assertEqual(mock_delete.call_count, 1)

    def test_co_owner_delete_removes_only_membership(self):
        user_a = self._make_user("user_a", "a@example.com")
        user_b = self._make_user("user_b", "b@example.com")
        school = self._make_school("Co School", "org_co")
        SchoolMembership.objects.create(user=user_a, school=school, role="owner")
        SchoolMembership.objects.create(user=user_b, school=school, role="owner")

        with self._mock_clerk_delete(return_value=Mock(status_code=200)):
            response = self._delete_account("user_a")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(clerk_user_id="user_a").exists())
        self.assertTrue(School.objects.filter(id=school.id).exists())
        self.assertTrue(
            SchoolMembership.objects.filter(user=user_b, school=school).exists())

    def test_non_owner_delete_removes_only_membership(self):
        user = self._make_user("user_teacher", "teacher@example.com")
        school = self._make_school("Teacher School", "org_teacher")
        SchoolMembership.objects.create(user=user, school=school, role="teacher")

        with self._mock_clerk_delete(return_value=Mock(status_code=200)):
            response = self._delete_account("user_teacher")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(clerk_user_id="user_teacher").exists())
        self.assertTrue(School.objects.filter(id=school.id).exists())

    def test_mixed_ownership_across_schools(self):
        user = self._make_user("user_mixed", "mixed@example.com")
        other_owner = self._make_user("user_other_owner", "other_owner@example.com")
        other_teacher = self._make_user("user_other_teacher", "other_teacher@example.com")

        school_a = self._make_school("Sole Owned A", "org_a")
        school_b = self._make_school("Co Owned B", "org_b")
        school_c = self._make_school("Teacher C", "org_c")

        SchoolMembership.objects.create(user=user, school=school_a, role="owner")
        SchoolMembership.objects.create(user=user, school=school_b, role="owner")
        SchoolMembership.objects.create(user=other_owner, school=school_b, role="owner")
        SchoolMembership.objects.create(user=user, school=school_c, role="teacher")
        SchoolMembership.objects.create(user=other_teacher, school=school_c, role="teacher")

        with self._mock_clerk_delete(return_value=Mock(status_code=200)):
            response = self._delete_account("user_mixed")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(School.objects.filter(id=school_a.id).exists())
        self.assertTrue(School.objects.filter(id=school_b.id).exists())
        self.assertTrue(School.objects.filter(id=school_c.id).exists())
        self.assertTrue(
            SchoolMembership.objects.filter(user=other_owner, school=school_b).exists())
        self.assertTrue(
            SchoolMembership.objects.filter(user=other_teacher, school=school_c).exists())

    def test_delete_succeeds_when_clerk_user_already_gone(self):
        self._make_user("user_gone", "gone@example.com")

        with self._mock_clerk_delete(return_value=Mock(status_code=404)) as mock_delete:
            response = self._delete_account("user_gone")

        # The actual claim under test: a 404 from Clerk does not trip the
        # ClerkDeleteError/502 path, isn't retried, and the local account is
        # really gone — i.e. it behaves exactly like the clean-success case.
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data["message"], "Account deleted successfully")
        self.assertEqual(mock_delete.call_count, 1)
        self.assertFalse(User.objects.filter(clerk_user_id="user_gone").exists())

    def test_clerk_delete_fails_after_retries_returns_error_but_db_already_gone(self):
        self._make_user("user_fail", "fail@example.com")

        with self._mock_clerk_delete(return_value=Mock(status_code=500, text="error")) as mock_delete:
            with patch("backend.services.clerk_client.time.sleep"):
                response = self._delete_account("user_fail")

        self.assertEqual(response.status_code, 502)
        self.assertEqual(mock_delete.call_count, 3)
        self.assertFalse(User.objects.filter(clerk_user_id="user_fail").exists())

    def test_clerk_delete_retries_then_succeeds(self):
        self._make_user("user_retry", "retry@example.com")

        with self._mock_clerk_delete(
            side_effect=[Mock(status_code=500, text="error"), Mock(status_code=200)]
        ) as mock_delete:
            with patch("backend.services.clerk_client.time.sleep"):
                response = self._delete_account("user_retry")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_delete.call_count, 2)
        self.assertFalse(User.objects.filter(clerk_user_id="user_retry").exists())

    def test_post_delete_token_resolves_to_anonymous(self):
        self._make_user("user_bye", "bye@example.com")

        with self._mock_clerk_delete(return_value=Mock(status_code=200)):
            self._delete_account("user_bye")

        payload = {"sub": "user_bye", "email": "bye@example.com", "email_verified": True}
        with self._mock_clerk_token(payload):
            response = self.client.get(
                "/backend/me/", HTTP_AUTHORIZATION="Bearer test-token")

        self.assertEqual(response.status_code, 401)

    def test_kiosk_cannot_self_delete(self):
        user = self._make_user("user_kiosk", "kiosk@example.com")
        school = self._make_school("Kiosk School", "org_kiosk")
        SchoolMembership.objects.create(user=user, school=school, role="kiosk")

        with self._mock_clerk_delete(return_value=Mock(status_code=200)) as mock_delete:
            response = self._delete_account("user_kiosk")

        self.assertEqual(response.status_code, 403)
        self.assertTrue(User.objects.filter(clerk_user_id="user_kiosk").exists())
        self.assertTrue(School.objects.filter(id=school.id).exists())
        self.assertTrue(
            SchoolMembership.objects.filter(user=user, school=school).exists())
        mock_delete.assert_not_called()

    def test_db_cascade_failure_blocks_clerk_call(self):
        user = self._make_user("user_dbfail", "dbfail@example.com")
        school = self._make_school("DB Fail School", "org_dbfail")
        SchoolMembership.objects.create(user=user, school=school, role="owner")

        with patch(
            "backend.views.auth.School.objects.filter",
            side_effect=RuntimeError("boom"),
        ):
            with self._mock_clerk_delete(return_value=Mock(status_code=200)) as mock_delete:
                response = self._delete_account("user_dbfail")

        self.assertEqual(response.status_code, 500)
        mock_delete.assert_not_called()
        self.assertTrue(User.objects.filter(clerk_user_id="user_dbfail").exists())
        self.assertTrue(School.objects.filter(id=school.id).exists())
        self.assertTrue(
            SchoolMembership.objects.filter(user=user, school=school).exists())

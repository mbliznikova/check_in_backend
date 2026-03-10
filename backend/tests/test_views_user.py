"""Tests for user-related views (get_user, today_classes_list, etc.)."""
import json

from .test_utils import BaseTestCase


class UserViewsTestCase(BaseTestCase):
    """Tests for user info and related endpoints."""

    def setUp(self):
        super().setUp()
        self.get_user_url = "/api/me/"
        self.today_classes_url = "/api/today_classes_list/"

    # TODO: Add tests for get_user (GET /me/)
    # TODO: Add tests for today_classes_list
    # TODO: Add tests for available_occurrence_time
    pass

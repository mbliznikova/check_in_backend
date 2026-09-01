"""Tests for per-school timezone support (School.timezone, school_now/school_today,
and the four "today"/"next occurrence" call sites that were localized to it)."""
import json
from datetime import date, datetime, time
from datetime import timezone as dt_timezone
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.urls import reverse

from backend.models import ClassModel, ClassOccurrence, Day, School, Schedule
from backend.tasks import create_class_occurrences
from backend.utils import is_valid_timezone, school_now, school_today
from backend.views.schedules import create_next_occurrence_for_schedule

from .test_utils import BaseTestCase

# A fixed UTC instant where America/Los_Angeles and Pacific/Kiritimati
# (UTC+14, the furthest-ahead IANA zone) land on different local calendar
# days: LA -> 2026-01-05 (Monday), Kiritimati -> 2026-01-06 (Tuesday).
BOUNDARY_UTC_INSTANT = datetime(2026, 1, 6, 2, 0, 0, tzinfo=dt_timezone.utc)


class TimezoneUtilsTestCase(BaseTestCase):
    def test_is_valid_timezone(self):
        self.assertTrue(is_valid_timezone("America/New_York"))
        self.assertFalse(is_valid_timezone("Not/AZone"))

    def test_school_now_uses_school_timezone(self):
        self.school.timezone = "Europe/London"
        self.school.save()
        with patch("backend.utils.django_timezone.now", return_value=BOUNDARY_UTC_INSTANT):
            now = school_now(self.school)
        self.assertEqual(str(now.tzinfo), "Europe/London")

    def test_school_today_differs_across_timezones_at_day_boundary(self):
        self.school.timezone = "America/Los_Angeles"
        self.school.save()
        ki_school = School.objects.create(
            name="Kiritimati School", clerk_org_id="ki_org",
            timezone="Pacific/Kiritimati")

        with patch("backend.utils.django_timezone.now", return_value=BOUNDARY_UTC_INSTANT):
            la_today = school_today(self.school)
            ki_today = school_today(ki_school)

        self.assertEqual(la_today, date(2026, 1, 5))
        self.assertEqual(ki_today, date(2026, 1, 6))
        self.assertNotEqual(la_today, ki_today)


class SchoolTimezoneModelTestCase(BaseTestCase):
    def test_invalid_timezone_raises_on_save(self):
        school = School(
            name="Bad TZ School", clerk_org_id="bad_tz_org",
            timezone="Not/AZone")
        with self.assertRaises(ValidationError):
            school.save()

    def test_valid_non_default_timezone_saves(self):
        school = School.objects.create(
            name="London School", clerk_org_id="london_org",
            timezone="Europe/London")
        self.assertEqual(school.timezone, "Europe/London")

    def test_default_timezone(self):
        school = School.objects.create(
            name="Default TZ School", clerk_org_id="default_tz_org")
        self.assertEqual(school.timezone, "America/Los_Angeles")


class SchoolTimezoneApiTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.edit_school_url = reverse("edit_school", args=[self.school.id])

    def test_patch_valid_timezone_succeeds(self):
        response = self.client.patch(
            self.edit_school_url,
            json.dumps({"timezone": "Europe/London"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data["timezone"], "Europe/London")
        self.school.refresh_from_db()
        self.assertEqual(self.school.timezone, "Europe/London")

    def test_patch_invalid_timezone_returns_400(self):
        response = self.client.patch(
            self.edit_school_url,
            json.dumps({"timezone": "Not/AZone"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.school.refresh_from_db()
        self.assertEqual(self.school.timezone, "America/Los_Angeles")


class CreateClassOccurrencesTimezoneTestCase(BaseTestCase):
    """Covers backend/tasks.py: create_class_occurrences() (Celery beat task)."""

    def setUp(self):
        super().setUp()
        self.school.timezone = "America/Los_Angeles"
        self.school.save()

        self.ki_school = School.objects.create(
            name="Kiritimati School", clerk_org_id="ki_org",
            timezone="Pacific/Kiritimati")

        self.monday, _ = Day.objects.get_or_create(name="Monday")

        self.la_class = ClassModel.objects.create(
            school=self.school, name="LA Class", duration_minutes=60)
        self.ki_class = ClassModel.objects.create(
            school=self.ki_school, name="KI Class", duration_minutes=60)

        self.la_schedule = Schedule.objects.create(
            class_model=self.la_class, school=self.school, day=self.monday,
            class_time=time(10, 0))
        self.ki_schedule = Schedule.objects.create(
            class_model=self.ki_class, school=self.ki_school, day=self.monday,
            class_time=time(10, 0))

    def test_each_school_uses_its_own_timezone(self):
        with patch("backend.utils.django_timezone.now", return_value=BOUNDARY_UTC_INSTANT):
            create_class_occurrences()

        la_occurrence = ClassOccurrence.objects.get(class_model=self.la_class)
        ki_occurrence = ClassOccurrence.objects.get(class_model=self.ki_class)

        # LA's "next Monday" as of the boundary instant is today (2026-01-05,
        # already a Monday); Kiritimati's is a week out (2026-01-12).
        self.assertEqual(la_occurrence.actual_date, date(2026, 1, 5))
        self.assertEqual(ki_occurrence.actual_date, date(2026, 1, 12))

    def test_memoizes_next_monday_per_school(self):
        tuesday, _ = Day.objects.get_or_create(name="Tuesday")
        Schedule.objects.create(
            class_model=self.ki_class, school=self.ki_school, day=tuesday,
            class_time=time(11, 0))

        with patch("backend.utils.django_timezone.now", return_value=BOUNDARY_UTC_INSTANT):
            create_class_occurrences()

        dates = sorted(
            occ.actual_date
            for occ in ClassOccurrence.objects.filter(school=self.ki_school)
        )
        self.assertEqual(dates, [date(2026, 1, 12), date(2026, 1, 13)])


class CreateNextOccurrenceForScheduleTimezoneTestCase(BaseTestCase):
    """Covers backend/views/schedules.py: create_next_occurrence_for_schedule()."""

    def test_uses_schedules_school_timezone(self):
        ki_school = School.objects.create(
            name="Kiritimati School 2", clerk_org_id="ki_org_2",
            timezone="Pacific/Kiritimati")
        tuesday, _ = Day.objects.get_or_create(name="Tuesday")
        ki_class = ClassModel.objects.create(
            school=ki_school, name="KI Class 2", duration_minutes=45)
        schedule = Schedule.objects.create(
            class_model=ki_class, school=ki_school, day=tuesday,
            class_time=time(9, 0))

        with patch("backend.utils.django_timezone.now", return_value=BOUNDARY_UTC_INSTANT):
            occurrence = create_next_occurrence_for_schedule(schedule)

        self.assertIsNotNone(occurrence)
        # Kiritimati's "today" at the boundary instant is 2026-01-06, a
        # Tuesday — matching the schedule's day, so it's the next occurrence.
        self.assertEqual(occurrence.actual_date, date(2026, 1, 6))


class TodayEndpointsTimezoneTestCase(BaseTestCase):
    """Covers today_class_occurrences() and today_classes_list()."""

    def setUp(self):
        super().setUp()
        self.school.timezone = "Pacific/Kiritimati"
        self.school.save()

        self.tuesday, _ = Day.objects.get_or_create(name="Tuesday")
        self.monday, _ = Day.objects.get_or_create(name="Monday")

        self.class_model = ClassModel.objects.create(
            school=self.school, name="KI Endpoint Class", duration_minutes=30)

        # Dated "today" in the school's timezone (2026-01-06).
        self.ki_today_occurrence = ClassOccurrence.objects.create(
            school=self.school, class_model=self.class_model,
            fallback_class_name=self.class_model.name,
            planned_date=date(2026, 1, 6), actual_date=date(2026, 1, 6),
            planned_start_time=time(9, 0), actual_start_time=time(9, 0),
            planned_duration=30, actual_duration=30,
        )
        # Dated "today" in settings.TIME_ZONE (LA) but not in the school's
        # own timezone — must be excluded once localized correctly.
        self.la_today_occurrence = ClassOccurrence.objects.create(
            school=self.school, class_model=self.class_model,
            fallback_class_name=self.class_model.name,
            planned_date=date(2026, 1, 5), actual_date=date(2026, 1, 5),
            planned_start_time=time(9, 0), actual_start_time=time(10, 0),
            planned_duration=30, actual_duration=30,
        )

        Schedule.objects.create(
            class_model=self.class_model, school=self.school, day=self.tuesday,
            class_time=time(9, 0))

    def test_today_class_occurrences_uses_school_timezone(self):
        with patch("backend.utils.django_timezone.now", return_value=BOUNDARY_UTC_INSTANT):
            response = self.client.get(reverse("today_class_occurrences"))

        self.assertEqual(response.status_code, 200)
        ids = [item["id"] for item in json.loads(response.content)["response"]]
        self.assertIn(self.ki_today_occurrence.id, ids)
        self.assertNotIn(self.la_today_occurrence.id, ids)

    def test_today_classes_list_uses_school_timezone(self):
        with patch("backend.utils.django_timezone.now", return_value=BOUNDARY_UTC_INSTANT):
            response = self.client.get(reverse("today_classes_list"))

        self.assertEqual(response.status_code, 200)
        class_ids = [item["id"] for item in json.loads(response.content)["response"]]
        self.assertIn(self.class_model.id, class_ids)

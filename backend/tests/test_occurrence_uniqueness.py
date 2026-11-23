"""
ClassOccurrence is unique per (school, class_model, actual_date,
actual_start_time). Orphans (class deleted -> class_model NULL) and
renamed classes keep their old fallback_class_name and must not block a
class that now uses that name.
"""
import json
from datetime import time, timedelta
from unittest.mock import patch

from django.urls import reverse

from ..models import ClassModel, ClassOccurrence, Day, Schedule, School
from ..tasks import create_class_occurrences
from ..utils import school_today
from .test_utils import BaseTestCase

SLOT_TAKEN_MESSAGE = "This class already has an occurrence at that date and time"


class OccurrenceUniquenessBase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.today = school_today(self.school)
        self.slot_time = time(8, 0)

    def make_occurrence(self, school=None, class_model=None,
                        fallback_class_name="", date=None, start=None):
        date = date or self.today
        start = start or self.slot_time
        return ClassOccurrence.objects.create(
            school=school or self.school,
            class_model=class_model,
            fallback_class_name=fallback_class_name,
            planned_date=date, actual_date=date,
            planned_start_time=start, actual_start_time=start,
            planned_duration=60, actual_duration=60,
        )

    def post_schedule(self, class_model, day_name, class_time="08:00:00"):
        return self.client.post(
            reverse("schedules"),
            json.dumps({
                "classId": class_model.id,
                "day": day_name,
                "classTime": class_time,
            }),
            content_type="application/json",
        )


class ScheduleOverOrphanTestCase(OccurrenceUniquenessBase):
    """POST /schedules/ when an old occurrence shares the name and slot."""

    def setUp(self):
        super().setUp()
        self.today_name = self.today.strftime("%A")
        Day.objects.get_or_create(name=self.today_name)

    def test_recreated_class_can_be_scheduled_over_orphan(self):
        old = ClassModel.objects.create(name="X", school=self.school)
        orphan = self.make_occurrence(class_model=old)
        response = self.client.delete(reverse("delete_class", args=[old.id]))
        self.assertEqual(response.status_code, 200)

        new = ClassModel.objects.create(name="X", school=self.school)
        response = self.post_schedule(new, self.today_name)

        self.positive_response_helper(
            response, 200, "Schedule was created successfully")
        self.assertTrue(ClassOccurrence.objects.filter(
            class_model=new, actual_date=self.today,
            actual_start_time=self.slot_time).exists())
        orphan.refresh_from_db()
        self.assertIsNone(orphan.class_model)
        self.assertEqual(orphan.fallback_class_name, "X")

    def test_new_class_with_renamed_class_old_name_can_be_scheduled(self):
        renamed = ClassModel.objects.create(name="A", school=self.school)
        self.make_occurrence(class_model=renamed)
        self.client.patch(
            reverse("edit_class", args=[renamed.id]),
            json.dumps({"name": "B"}),
            content_type="application/json",
        )

        new = ClassModel.objects.create(name="A", school=self.school)
        response = self.post_schedule(new, self.today_name)

        self.positive_response_helper(
            response, 200, "Schedule was created successfully")
        self.assertTrue(
            ClassOccurrence.objects.filter(class_model=new).exists())

    def test_schedule_rolls_back_when_occurrence_creation_fails(self):
        class_model = ClassModel.objects.create(
            name="Y", school=self.school)

        with patch(
            "backend.views.schedules.create_next_occurrence_for_schedule",
            side_effect=RuntimeError("boom"),
        ):
            response = self.post_schedule(class_model, self.today_name)

        self.assertEqual(response.status_code, 500)
        self.assertFalse(
            Schedule.objects.filter(class_model=class_model).exists())


class DeleteClassWithOrphanTestCase(OccurrenceUniquenessBase):
    def test_delete_class_when_orphan_with_same_name_and_slot_exists(self):
        """Two orphans may share name/date/time (no rule for NULL class)."""
        self.make_occurrence(fallback_class_name="X")
        class_model = ClassModel.objects.create(name="X", school=self.school)
        self.make_occurrence(class_model=class_model)

        response = self.client.delete(
            reverse("delete_class", args=[class_model.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ClassOccurrence.objects.filter(
            class_model__isnull=True, fallback_class_name="X",
            actual_date=self.today,
            actual_start_time=self.slot_time).count(), 2)


class CreateClassOccurrencesOrphanTestCase(OccurrenceUniquenessBase):
    def test_orphan_with_same_name_and_slot_does_not_block_batch(self):
        monday, _ = Day.objects.get_or_create(name="Monday")
        next_monday = self.today + timedelta(
            days=(8 - self.today.isoweekday()) % 7)

        class_model = ClassModel.objects.create(name="X", school=self.school)
        Schedule.objects.create(
            class_model=class_model, school=self.school, day=monday,
            class_time=self.slot_time)
        self.make_occurrence(fallback_class_name="X", date=next_monday)

        other_school = School.objects.create(
            name="Other School", clerk_org_id="other_org")
        other_class = ClassModel.objects.create(
            name="Z", school=other_school)
        Schedule.objects.create(
            class_model=other_class, school=other_school, day=monday,
            class_time=self.slot_time)

        create_class_occurrences()

        self.assertTrue(ClassOccurrence.objects.filter(
            class_model=class_model, actual_date=next_monday).exists())
        self.assertTrue(
            ClassOccurrence.objects.filter(class_model=other_class).exists())


class OccurrenceEndpointsSlotTestCase(OccurrenceUniquenessBase):
    """POST /class_occurrences/ and PATCH .../edit/ return 409 on a clash."""

    def setUp(self):
        super().setUp()
        self.class_model = ClassModel.objects.create(
            name="X", school=self.school)
        self.existing = self.make_occurrence(class_model=self.class_model)

    def post_occurrence(self, class_model):
        return self.client.post(
            reverse("class_occurrences"),
            json.dumps({
                "classModel": class_model.id,
                "fallbackClassName": class_model.name,
                "plannedDate": self.today.isoformat(),
                "plannedStartTime": "08:00",
            }),
            content_type="application/json",
        )

    def test_post_occurrence_on_taken_slot_returns_409(self):
        response = self.post_occurrence(self.class_model)

        self.error_response_helper(response, 409, SLOT_TAKEN_MESSAGE)
        self.assertEqual(ClassOccurrence.objects.filter(
            class_model=self.class_model).count(), 1)

    def test_post_occurrence_same_slot_other_class_succeeds(self):
        other = ClassModel.objects.create(name="Other", school=self.school)

        response = self.post_occurrence(other)

        self.positive_response_helper(
            response, 200, "Class occurrence was created successfully")

    def test_patch_occurrence_onto_taken_slot_returns_409(self):
        later = self.make_occurrence(
            class_model=self.class_model, start=time(10, 0))

        response = self.client.patch(
            reverse("edit_occurrence", args=[later.id]),
            json.dumps({"actualStartTime": "08:00"}),
            content_type="application/json",
        )

        self.error_response_helper(response, 409, SLOT_TAKEN_MESSAGE)
        later.refresh_from_db()
        self.assertEqual(later.actual_start_time, time(10, 0))

    def test_patch_occurrence_keeping_its_own_slot_succeeds(self):
        response = self.client.patch(
            reverse("edit_occurrence", args=[self.existing.id]),
            json.dumps({
                "actualDate": self.today.isoformat(),
                "actualStartTime": "08:00",
                "notes": "same slot",
            }),
            content_type="application/json",
        )

        self.positive_response_helper(
            response, 200, "Class Occurrence was updated successfully")

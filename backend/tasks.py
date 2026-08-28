import logging
from datetime import timedelta

from celery import shared_task

from .models import ClassOccurrence, Schedule
from .utils import school_today

logger = logging.getLogger(__name__)


@shared_task
def create_class_occurrences():
    """
    Create ClassOccurrence entries for all schedules for the upcoming week.
    """

    weekday_map = {
        "monday": 1,
        "tuesday": 2,
        "wednesday": 3,
        "thursday": 4,
        "friday": 5,
        "saturday": 6,
        "sunday": 7,
    }

    schedules = Schedule.objects.select_related(
        "class_model", "day", "school").all()

    occurrences_to_create = []
    next_monday_by_school = {}

    for schedule in schedules:
        try:
            school = schedule.school
            next_monday_date = next_monday_by_school.get(school.id)
            if next_monday_date is None:
                # Get the next Monday (weekdays start from 1)
                # NOTE: this must be computed per schedule's school timezone,
                # not once globally — schools outside settings.TIME_ZONE need
                # their own "today"/"next Monday".
                today = school_today(school)
                days_until_next_monday = (8 - today.isoweekday()) % 7
                next_monday_date = today + \
                    timedelta(days=days_until_next_monday)
                next_monday_by_school[school.id] = next_monday_date
                logger.info(
                    f"Creating class occurrences for school {school.id}. "
                    f"The next Monday will be {next_monday_date}")

            weekday_num = weekday_map[schedule.day.name.lower()]
            occurrence_date = next_monday_date + timedelta(days=weekday_num - 1)

            exist = ClassOccurrence.objects.filter(
                class_model=schedule.class_model,
                actual_date=occurrence_date,
                actual_start_time=schedule.class_time,
            ).exists()

            if exist:
                logger.debug(
                    f"Skipping scheduling class {
                        schedule.class_model} for {occurrence_date} {
                        schedule.class_time} because of duplication.")
                continue

            occurrence = ClassOccurrence(
                school=schedule.school,
                class_model=schedule.class_model,
                fallback_class_name=schedule.class_model.name,
                schedule=schedule,
                planned_date=occurrence_date,
                actual_date=occurrence_date,
                planned_start_time=schedule.class_time,
                actual_start_time=schedule.class_time,
                planned_duration=schedule.class_model.duration_minutes,
                actual_duration=schedule.class_model.duration_minutes,
                is_cancelled=False,
            )

            occurrences_to_create.append(occurrence)
        except Exception:
            logger.exception("Failed to process schedule id=%s", schedule.id)

    if occurrences_to_create:
        ClassOccurrence.objects.bulk_create(occurrences_to_create)
        logger.info(
            f"Created {
                len(occurrences_to_create)} new class occurrences.")
    else:
        logger.info("No new class occurrences to create")

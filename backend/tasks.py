from datetime import date, timedelta

from celery import shared_task
from django.utils import timezone

from .models import ClassOccurrence, Schedule, ClassModel, Day

@shared_task
def create_class_occurrences():
    """
    Create ClassOccurrence entries for all schedules for the upcoming week.
    """

    # Get the next Monday (weekdays start from 1)
    today = date.today()
    days_until_next_monday = (8 - today.isoweekday()) % 7
    next_monday_date = today + timedelta(days=days_until_next_monday)

    print(f"Creating class occurrence. The next Mondays will be {next_monday_date}")

    weekday_map = {
        "monday": 1,
        "tuesday": 2,
        "wednesday": 3,
        "thursday": 4,
        "friday": 5,
        "saturday": 6,
        "sunday": 7,
    }

    schedules = Schedule.objects.select_related("class_model", "day").all()

    occurrences_to_create = []

    for schedule in schedules:
        weekday_num = weekday_map[schedule.day.name.lower()]
        occurrence_date = next_monday_date + timedelta(days=weekday_num - 1)

        exist = ClassOccurrence.objects.filter(
            class_model=schedule.class_model,
            actual_date=occurrence_date,
            actual_start_time=schedule.class_time,
        ).exists()

        if exist:
            print(f"Skipping scheduling class {schedule.class_model} for {occurrence_date} {schedule.class_time} because of duplication.")
            continue

        occurrence = ClassOccurrence(
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

    
    if occurrences_to_create:
        ClassOccurrence.objects.bulk_create(occurrences_to_create)
        print(f"Created {len(occurrences_to_create)} new class occurrences.")
    else:
        print("No new class occurrences to create")


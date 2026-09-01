from zoneinfo import ZoneInfo, available_timezones

from django.utils import timezone as django_timezone

_VALID_TIMEZONES = available_timezones()


def is_valid_timezone(tz_name):
    return tz_name in _VALID_TIMEZONES


def school_now(school):
    return django_timezone.localtime(
        django_timezone.now(), timezone=ZoneInfo(school.timezone)
    )


def school_today(school):
    return school_now(school).date()

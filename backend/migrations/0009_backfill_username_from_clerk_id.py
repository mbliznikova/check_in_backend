from django.db import migrations
from django.db.models import F


def backfill_username(apps, schema_editor):
    User = apps.get_model("backend", "User")
    # clerk_user_id is unique, so setting username = clerk_user_id for these
    # rows cannot collide with the username unique constraint. Rows with no
    # clerk_user_id (e.g. a createsuperuser admin row) are left untouched.
    User.objects.filter(clerk_user_id__isnull=False).exclude(
        clerk_user_id=""
    ).update(username=F("clerk_user_id"))


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("backend", "0008_school_timezone"),
    ]

    operations = [
        migrations.RunPython(backfill_username, noop_reverse),
    ]

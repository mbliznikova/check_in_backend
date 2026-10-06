from django.db import migrations, models
from django.db.models import Count


def check_no_duplicate_emails(apps, schema_editor):
    User = apps.get_model("backend", "User")
    duplicates = (
        User.objects.values("email")
        .annotate(count=Count("id"))
        .filter(count__gt=1)
    )
    if duplicates.exists():
        emails = ", ".join(d["email"] for d in duplicates)
        raise RuntimeError(
            "Cannot add unique constraint on User.email: duplicate emails "
            f"found: {emails}"
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("backend", "0009_backfill_username_from_clerk_id"),
    ]

    operations = [
        migrations.RunPython(check_no_duplicate_emails, noop_reverse),
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(
                max_length=254, blank=True, unique=True,
                verbose_name="email address",
            ),
        ),
    ]

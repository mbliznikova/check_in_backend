# Generated by Django 5.1.6 on 2025-03-18 18:13

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0006_alter_attendance_attendance_date'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='attendance',
            unique_together={('student_id', 'class_id', 'attendance_date')},
        ),
    ]

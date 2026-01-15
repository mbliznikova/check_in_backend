import datetime

from django.db import models
from django.utils.timezone import now
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    clerk_user_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        )
    ROLE_CHOICES = [
        ("kiosk", "Kiosk"),
        ("teacher", "Teacher"),
        ("admin", "Administrator"),
        ("owner", "Owner"),
    ]
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='teacher')

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

class Student(models.Model):
    id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    is_liability_form_sent = models.BooleanField(default=False)
    emergency_contacts = models.CharField(max_length=255, blank=True, default="")

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

class ClassModel(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)
    duration_minutes = models.PositiveIntegerField(default=60)
    is_recurring = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Day(models.Model):
    name = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name

class Schedule(models.Model):
    class_model = models.ForeignKey(ClassModel, on_delete=models.CASCADE)
    day = models.ForeignKey(Day, on_delete=models.CASCADE)
    class_time = models.TimeField()

    class Meta:
        unique_together = ("day", "class_time")

    def __str__(self):
        return f'{self.class_model.name} on {self.day.name} at {self.class_time}'

class ClassOccurrence(models.Model):
    id = models.AutoField(primary_key=True)
    class_model = models.ForeignKey(ClassModel, on_delete=models.SET_NULL, null=True, blank=True) # TODO: rename to class_id?
    fallback_class_name = models.CharField(max_length=100, blank=True)
    schedule = models.ForeignKey(Schedule, on_delete=models.SET_NULL, null=True, blank=True)
    planned_date = models.DateField()
    actual_date = models.DateField()
    planned_start_time = models.TimeField()
    actual_start_time = models.TimeField()
    planned_duration = models.PositiveIntegerField()
    actual_duration = models.PositiveIntegerField()
    is_cancelled = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default='')

    # TODO: add indexing?

    @property
    def safe_class_id(self):
        return self.class_model.id if self.class_model else None

    @property
    def safe_class_name(self):
        return self.class_model.name if self.class_model else self.fallback_class_name

    def __str__(self):
        date = self.actual_date or self.planned_date or "unknown date"
        time = self.actual_start_time or self.planned_start_time or "unknown time"
        return f'{self.safe_class_name} at {date} on {time}'

    class Meta:
        unique_together = ("fallback_class_name", "actual_date", "actual_start_time")

    def save(self, *args, **kwargs):
        if self.class_model and not self.fallback_class_name:
            self.fallback_class_name = self.class_model.name

        super().save(*args, **kwargs)


class Attendance(models.Model):
    id = models.AutoField(primary_key=True)
    # TODO: rename student_id and class_id to student_model and class_model?
    # Backlog? Since it would require changes in FE as well.
    student_id = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True) # TODO: rename to student?
    fallback_class_id = models.IntegerField(null=True, blank=True)
    fallback_student_id = models.IntegerField(null=True, blank=True)
    student_first_name = models.CharField(max_length=50, blank=True)
    student_last_name = models.CharField(max_length=50, blank=True)
    class_name = models.CharField(max_length=50, blank=True) # TODO: rename to fallback_class_name?
    class_occurrence = models.ForeignKey(ClassOccurrence, on_delete=models.SET_NULL, null=True, blank=True)
    attendance_date = models.DateField(default=datetime.date.today)
    is_showed_up = models.BooleanField(default=True)

    @property
    def safe_student_id(self):
        return self.student_id.id if self.student_id else self.fallback_student_id

    @property
    def safe_class_id(self):
        if self.class_occurrence:
            return self.class_occurrence.safe_class_id
        return self.fallback_class_id

    #TODO: add safe class occurrence? Like name - date? Or just id?
    @property
    def safe_occurrence_id(self):
        return self.class_occurrence.id if self.class_occurrence else None # TODO: have it always present, like fallback?

    @property
    def safe_class_name(self):
        if self.class_occurrence:
            return self.class_occurrence.safe_class_name
        return self.class_name or "Unknown" # TODO: handle 'Attendance' object has no attribute 'fallback_class_name'

    class Meta:
        # Make it unique for day-month-year? class occurrence?
        unique_together = ("student_id", "class_occurrence")

    def __str__(self):
        return f"{self.safe_student_id} - {self.safe_class_name} ({self.attendance_date})"

    def save(self, *args, **kwargs):
        if self.student_id:
            self.fallback_student_id = self.student_id.id
            if not self.student_first_name:
                self.student_first_name = self.student_id.first_name
            if not self.student_last_name:
                self.student_last_name = self.student_id.last_name

        if self.class_occurrence:
            class_model = self.class_occurrence.class_model
            if class_model:
                self.fallback_class_id = class_model.id
                self.class_name = class_model.name
            elif not self.class_name:
                self.fallback_class_id = self.class_occurrence.safe_class_id # TODO: still not safe enough
                self.class_name = self.class_occurrence.fallback_class_name

            if not self.attendance_date:
                self.attendance_date = self.class_occurrence.actual_date

        super().save(*args, **kwargs)

class Payment(models.Model):
    id = models.AutoField(primary_key=True)
    # TODO: rename student_id and class_id to student_model and class_model?
    student_id = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True)
    class_id = models.ForeignKey(ClassModel, on_delete=models.SET_NULL, null=True)
    student_name = models.CharField(max_length=50, blank=True)
    class_name = models.CharField(max_length=50, blank=True)
    amount = models.FloatField()
    payment_date = models.DateTimeField(default=now)
    payment_month = models.IntegerField()
    payment_year = models.IntegerField()

    def save(self, *args, **kwargs):
        if self.student_id and not self.student_name:
            self.student_name = f"{self.student_id.first_name} {self.student_id.last_name}"
        if self.class_id and not self.class_name:
            self.class_name = f"{self.class_id.name}"
        super().save(*args, **kwargs)

class Price(models.Model):
    id = models.AutoField(primary_key=True)
    class_id = models.ForeignKey(ClassModel, on_delete=models.CASCADE)
    amount = models.FloatField()

    class Meta:
        unique_together = ("class_id",)

class MonthlyPaymentsSummary(models.Model):
    id = models.AutoField(primary_key=True)
    summary_date = models.DateField(help_text="Only the month and year are meaningful. Day will always be set to 1.")
    amount = models.FloatField()

    def save(self, *args, **kwargs):
        if self.summary_date:
            self.summary_date = self.summary_date.replace(day=1)
        super().save(*args, **kwargs)

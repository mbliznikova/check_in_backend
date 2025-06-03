import datetime

from django.db import models
from django.utils import timezone

class Student(models.Model):
    id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

class ClassModel(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)

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
        unique_together = ("class_model", "day", "class_time")

    def __str__(self):
        return f'{self.class_model.name} on {self.day.name} at {self.class_time}'

class Attendance(models.Model):
    id = models.AutoField(primary_key=True)
    # TODO: rename student_id and class_id to student_model and class_model?
    # Backlog? Since it would require changes in FE as well.
    student_id = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True)
    class_id = models.ForeignKey(ClassModel, on_delete=models.SET_NULL, null=True)
    student_name = models.CharField(max_length=50, blank=True)
    class_name = models.CharField(max_length=50, blank=True)
    attendance_date = models.DateField(default=datetime.date.today)
    is_showed_up = models.BooleanField(default=True)

    class Meta:
        # Make it unique for day-month-year?
        unique_together = ("student_id", "class_id", "attendance_date")

    def save(self, *args, **kwargs):
        if self.student_id and not self.student_name:
            self.student_name = f"{self.student_id.first_name} {self.student_id.last_name}"
        if self.class_id and not self.class_name:
            self.class_name = f"{self.class_id.name}"
        super().save(*args, **kwargs)

class Payment(models.Model):
    id = models.AutoField(primary_key=True)
    # TODO: rename student_id and class_id to student_model and class_model?
    student_id = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True)
    class_id = models.ForeignKey(ClassModel, on_delete=models.SET_NULL, null=True)
    student_name = models.CharField(max_length=50, blank=True)
    class_name = models.CharField(max_length=50, blank=True)
    amount = models.FloatField()
    payment_date = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        if self.student_id and not self.student_name:
            self.student_name = f"{self.student_id.first_name} {self.student_id.last_name}"
        if self.class_id and not self.class_name:
            self.class_name = f"{self.class_id.name}"
        if self.payment_date:
            self.payment_date = self.payment_date.replace(day=1)
        super().save(*args, **kwargs)

class Price(models.Model):
    id = models.AutoField(primary_key=True)
    class_id = models.ForeignKey(ClassModel, on_delete=models.CASCADE)
    amount = models.FloatField()

class MonthlyPaymentsSummary(models.Model):
    id = models.AutoField(primary_key=True)
    summary_date = models.DateField(help_text="Only the month and year are meaningful. Day will always be set to 1.")
    amount = models.FloatField()

    def save(self, *args, **kwargs):
        if self.summary_date:
            self.summary_date = self.summary_date.replace(day=1)
        super().save(*args, **kwargs)

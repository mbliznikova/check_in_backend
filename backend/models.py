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
    student_id = models.ForeignKey(Student, on_delete=models.CASCADE)
    class_id = models.ForeignKey(ClassModel, on_delete=models.CASCADE)
    attendance_date = models.DateField(default=datetime.date.today)
    is_showed_up = models.BooleanField(default=True)

    class Meta:
        unique_together = ("student_id", "class_id", "attendance_date")

class Payments(models.Model):
    id = models.AutoField(primary_key=True)
    student_id = models.ForeignKey(Student, on_delete=models.CASCADE)
    class_id = models.ForeignKey(ClassModel, on_delete=models.CASCADE)
    amount = models.FloatField()
    payment_date = models.DateTimeField(default=timezone.now)
import re

from rest_framework import serializers
from .models import Student, ClassModel, Day, Schedule, Attendance, Payment, Price, MonthlyPaymentsSummary, ClassOccurrence

class CaseSerializer(serializers.ModelSerializer):
    """
    The basic serializer to convert between snake_case (Django models) and CamelCase (frontend).
    """
    def to_representation(self, instance):
        # From django model instance to dictionary with camelCase keys (of primitive datatypes)
        data = super().to_representation(instance)
        return {self.snake_to_camel(key): value for key, value in data.items()}
    
    def to_internal_value(self, data):
        # From dictionary of primitive datatypes (with camelCase keys) to dictionary with native values (with snake_keys)
        data = {self.camel_to_snake(key): value for key, value in data.items()}
        return super().to_internal_value(data)

    @staticmethod
    def dict_to_camel_case(dict_data):
        return {CaseSerializer.snake_to_camel(key): value for key, value in dict_data.items()}
    
    @staticmethod
    def snake_to_camel(snake_str):
        snake_str_parts = snake_str.split('_')
        return f'{snake_str_parts[0]}{''.join(x.title() for x in snake_str_parts[1:])}'
    
    @staticmethod
    def camel_to_snake(camel_str):
        return re.sub(r'(?<!^)(?=[A-Z])', '_', camel_str).lower()
    
    @staticmethod
    def camelize_selected_keys(d: dict, keys: list[str]):
        result = {}
        for key, value in d.items():
            if key in keys:
                result[CaseSerializer.snake_to_camel(key)] = value
            else:
                result[key] = value
        return result

class StudentSerializer(CaseSerializer):
    class Meta:
        model = Student
        fields = '__all__'

class ClassModelSerializer(CaseSerializer):
    class Meta:
        model = ClassModel
        fields = '__all__'

class ClassOccurrenceSerializer(CaseSerializer):
    class Meta:
        model = ClassOccurrence
        fields = '__all__'

class DaySerializer(CaseSerializer):
    class Meta:
        model = Day
        fields = '__all__'

class ScheduleSerializer(CaseSerializer):
    class Meta:
        model = Schedule
        fields = '__all__'

class AttendanceSerializer(CaseSerializer):
    class Meta:
        model = Attendance
        fields = '__all__'

class PaymentSerializer(CaseSerializer):
    class Meta:
        model = Payment
        fields = '__all__'

class PriceSerializer(CaseSerializer):
    class Meta:
        model = Price
        fields ='__all__'

class MonthlyPaymentsSummarySerializer(CaseSerializer):
    class Meta:
        model = MonthlyPaymentsSummary
        fields ='__all__'

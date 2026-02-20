import json

from backend.decorators import teacher_or_above
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime, parse_date, parse_time
from django.db.models import Sum
from django.utils.timezone import now, is_naive, make_aware
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from backend.models import ClassModel, Payment, Price, Student
from backend.serializers import PaymentSerializer, PriceSerializer
from backend.views.helpers import make_error_json_response, make_success_json_response


@teacher_or_above
@csrf_exempt
@require_http_methods(["GET", "POST"])
def prices(request):
    if request.method == "GET":
        prices = Price.objects.filter(
            school=request.school,
        )

        price_dict = {}

        for price in prices:
            inner = {
                "class_name": price.class_id.name,
                "amount": price.amount,
                "price_id": price.id,
            }
            inner = PriceSerializer.dict_to_camel_case(inner)
            price_dict[str(price.class_id.id)] = inner

        result = PriceSerializer.dict_to_camel_case(price_dict)

        response = {
            "response": result
        }

        return make_success_json_response(200, response_body=response)

    if request.method == "POST":
        try:
            request_body = json.loads(request.body)
            class_id = request_body.get("classId")
            amount = request_body.get("amount")

            if not class_id or not amount:
                return make_error_json_response("Missing required fields", 400)

            try:
                class_instance = ClassModel.objects.get(
                    id=class_id,
                    school=request.school,
                )
            except Exception:
                return make_error_json_response(f"Class {class_id} does not exist", 400)

            if Price.objects.filter(
                class_id=class_instance,
                school=request.school,
            ).exists():
                return make_error_json_response(f"Price already exists for class {class_id}", 400)

            data_to_write = {
                "class_id": class_instance.pk,
                "amount": amount
            }

            serializer = PriceSerializer(data=data_to_write)
            if serializer.is_valid():
                saved_price = serializer.save(school=request.school)
            else:
                return make_error_json_response(serializer.errors, 400)

            response = PriceSerializer.dict_to_camel_case({
                "message": "Price was created successfully",
                "price_id": saved_price.id,
                "class_id": saved_price.class_id_id,
                "amount": amount,
            })

            return make_success_json_response(200, response_body=response)

        except json.JSONDecodeError:
            return make_error_json_response("Invalid JSON", 400)


@teacher_or_above
@csrf_exempt
@require_http_methods(["PATCH"])
def edit_price(request, price_id):
    if request.method == "PATCH":
        try:
            price = Price.objects.get(
                id=price_id,
                school=request.school,
            )

            request_body = json.loads(request.body)
            amount = request_body.get("amount")

            data_to_write = {}

            if amount is not None:
                data_to_write["amount"] = amount

            serializer = PriceSerializer(price, data=data_to_write, partial=True)
            if serializer.is_valid():
                serializer.save(school=request.school)
            else:
                return make_error_json_response(serializer.errors, 400)

            response = PriceSerializer.dict_to_camel_case({
                "message": "Price was updated successfully",
                "id": price.id,
                **data_to_write,
            })

            return make_success_json_response(200, response_body=response)

        except Price.DoesNotExist:
            return make_error_json_response("Price not found", 404)


@teacher_or_above
@csrf_exempt
@require_http_methods(["GET", "POST"])
def payments(request):
    if request.method == "GET":
        payment_month_param = request.GET.get('month', now().month)
        payment_year_param = request.GET.get('year', now().year)
        payments = Payment.objects.filter(
            school=request.school,
        ).filter(
            payment_month=payment_month_param,
            payment_year=payment_year_param
        )
        serializer = PaymentSerializer(payments, many=True)

        response = {
            "response": serializer.data
        }

        return make_success_json_response(200, response_body=response)

    if request.method == "POST":
        try:
            request_body = json.loads(request.body)
            payment_data = request_body.get("paymentData", {})
            student_id = payment_data.get("studentId")
            class_id = payment_data.get("classId")
            student_name = payment_data.get("studentName")
            class_name = payment_data.get("className")
            amount = payment_data.get("amount")
            payment_date_str = payment_data.get("paymentDate")
            month = payment_data.get("month")
            year = payment_data.get("year")

            if not student_id or not class_id or not amount:
                return make_error_json_response("Missing required fields", 400)

            if not month or not year:
                return make_error_json_response("Missing required fields", 400)

            try:
                month = int(month)
                year = int(year)
            except (ValueError, TypeError):
                return make_error_json_response("Invalid date format for month or year", 400)

            if not student_name:
                try:
                    student = Student.objects.get(
                        id=student_id,
                        school=request.school,
                    )
                    student_name = f"{student.first_name} {student.last_name}"
                except Student.DoesNotExist:
                    return make_error_json_response("Student not found", 404)

            if not class_name:
                try:
                    cls = ClassModel.objects.get(
                        id=class_id,
                        school=request.school,
                    )
                    class_name = f"{cls.name}"
                except ClassModel.DoesNotExist:
                    return make_error_json_response("Class not found", 404)

            payment_date = parse_datetime(payment_date_str) if payment_date_str else None

            if payment_date is None and payment_date_str:
                return make_error_json_response("Invalid datetime format for payment date", 400)

            if not (1 <= month <= 12):
                return make_error_json_response("Invalid value for month: should be between 1 and 12", 400)

            if payment_date and is_naive(payment_date):
                payment_date = make_aware(payment_date)

            data_to_write = {
                "student_id": student_id,
                "class_id": class_id,
                "student_name": student_name,
                "class_name": class_name,
                "amount": amount,
                "payment_month": month,
                "payment_year": year,
            }

            if payment_date:
                data_to_write["payment_date"] = payment_date

            serializer = PaymentSerializer(data=data_to_write)

            if serializer.is_valid():
                saved_payment = serializer.save(school=request.school)
            else:
                return make_error_json_response(serializer.errors, 400)

            response = PaymentSerializer.dict_to_camel_case({
                "message": "Payment was successfully created",
                "payment_id": saved_payment.id,
                "student_id": saved_payment.student_id.id if saved_payment.student_id else None,
                "class_id": saved_payment.class_id.id if saved_payment.class_id else None,
                "student_name": saved_payment.student_name,
                "class_name": saved_payment.class_name,
                "amount": saved_payment.amount,
                "payment_date": saved_payment.payment_date.isoformat() if saved_payment.payment_date else None,
                "payment_month": saved_payment.payment_month,
                "payment_year": saved_payment.payment_year,
            })

            return make_success_json_response(200, response_body=response)

        except json.JSONDecodeError:
            return make_error_json_response("Invalid JSON", 400)


@teacher_or_above
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_payment(request, payment_id):
    try:
        payment_instance = Payment.objects.get(
            id=payment_id,
            school=request.school,
        )
        payment_instance_id = payment_instance.id
        payment_amount = payment_instance.amount

        payment_instance.delete()

        response = PaymentSerializer.dict_to_camel_case({
            "message": f"Payment {payment_instance_id} was deleted successfully",
            "payment_id": payment_instance_id,
            "payment_amount": payment_amount,
        })

        return make_success_json_response(200, response_body=response)

    except Payment.DoesNotExist:
        return make_error_json_response("Payment not found", 404)
    except Exception as e:
        return make_error_json_response("An internal error occurred", 500)


@teacher_or_above
def payment_summary(request):
    payment_month_param = request.GET.get("month", now().month)
    payment_year_param = request.GET.get("year", now().year)

    payment_summary = Payment.objects.filter(
        school=request.school,
        payment_year=payment_year_param,
        payment_month=payment_month_param,
    )

    new_summary = payment_summary.aggregate(Sum("amount"))["amount__sum"] or 0.0

    response = {
        "summary": new_summary
    }

    return make_success_json_response(200, response_body=response)

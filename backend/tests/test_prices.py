"""Tests for price management functionality."""
import json

from django.urls import reverse

from ..models import ClassModel, Price
from .test_utils import BaseTestCase


class PricesTestCase(BaseTestCase):
    """Tests for price endpoints (GET /prices/, POST /prices/)."""

    def setUp(self):
        super().setUp()
        self.prices_url = reverse("prices")
        self.class_model = ClassModel.objects.create(
            name="Test Class", school=self.school)

    def post_price(self, body):
        return self.client.post(
            self.prices_url, json.dumps(body),
            content_type="application/json")

    def test_create_price_successfully(self):
        response = self.post_price(
            {"classId": self.class_model.id, "amount": 50})

        self.positive_response_helper(
            response, 200, "Price was created successfully")
        self.assertEqual(
            Price.objects.get(class_id=self.class_model).amount, 50)

    def test_create_price_with_zero_amount(self):
        response = self.post_price(
            {"classId": self.class_model.id, "amount": 0})

        self.positive_response_helper(
            response, 200, "Price was created successfully")
        self.assertEqual(json.loads(response.content)["amount"], 0)
        self.assertEqual(
            Price.objects.get(class_id=self.class_model).amount, 0)

    def test_create_price_missing_amount(self):
        response = self.post_price({"classId": self.class_model.id})

        self.error_response_helper(response, 400, "Missing required fields")
        self.assertFalse(
            Price.objects.filter(class_id=self.class_model).exists())

    def test_create_price_missing_class_id(self):
        response = self.post_price({"amount": 10})

        self.error_response_helper(response, 400, "Missing required fields")

    def test_edit_price_to_zero_amount(self):
        price = Price.objects.create(
            class_id=self.class_model, school=self.school, amount=50)

        response = self.client.patch(
            reverse("edit_price", args=[price.id]),
            json.dumps({"amount": 0}),
            content_type="application/json")

        self.positive_response_helper(
            response, 200, "Price was updated successfully")
        price.refresh_from_db()
        self.assertEqual(price.amount, 0)

    # TODO: Add tests for price retrieval, delete

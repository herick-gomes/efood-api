import os

os.environ.setdefault("DJANGO_DEBUG", "1")

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from shop.models import Product, Restaurant, User


@pytest.fixture(autouse=True)
def clean_cache():
    cache.clear()


@pytest.fixture
def customer(db):
    return User.objects.create_user(username="customer", password="Strong!Password2026")


@pytest.fixture
def other(db):
    return User.objects.create_user(username="other", password="Strong!Password2026")


@pytest.fixture
def merchant(db):
    return User.objects.create_user(username="merchant", password="Strong!Password2026", role="merchant")


@pytest.fixture
def restaurant(merchant):
    return Restaurant.objects.create(owner=merchant, name="Demo kitchen", category="Brazilian")


@pytest.fixture
def product(restaurant):
    return Product.objects.create(restaurant=restaurant, name="Lunch bowl", price="25.50", stock=10)


@pytest.fixture
def client(customer):
    c = APIClient()
    c.force_authenticate(user=customer)
    return c


@pytest.fixture
def merchant_client(merchant):
    c = APIClient()
    c.force_authenticate(user=merchant)
    return c


@pytest.fixture
def payload(product):
    return {
        "items": [{"product_id": product.pk, "quantity": 2}],
        "delivery": {
            "receiver": "Demo Customer",
            "address": "Example Street",
            "city": "Niteroi",
            "zip_code": "24000-000",
            "number": "10",
        },
    }

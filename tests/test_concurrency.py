from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from django.db import close_old_connections, connection, connections
from rest_framework.test import APIClient

from shop.models import Order, Product, Restaurant, User


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("same_customer", [True, False])
def test_concurrent_checkout_is_idempotent_and_never_oversells(same_customer):
    if connection.vendor != "postgresql":
        pytest.skip("Requires PostgreSQL row locks.")
    merchant = User.objects.create_user(username="owner", role="merchant")
    first = User.objects.create_user(username="first")
    second = first if same_customer else User.objects.create_user(username="second")
    restaurant = Restaurant.objects.create(owner=merchant, name="Kitchen", category="Test")
    product = Product.objects.create(restaurant=restaurant, name="Last item", price="19.90", stock=1)
    payload = {
        "items": [{"product_id": product.pk, "quantity": 1}],
        "delivery": {
            "receiver": "Test Customer",
            "address": "Test Street",
            "city": "Test City",
            "number": "1",
            "zip_code": "24000000",
        },
    }
    key = str(uuid4())
    barrier = Barrier(2)

    def checkout(user_id):
        close_old_connections()
        try:
            client = APIClient()
            client.force_authenticate(user=User.objects.get(pk=user_id))
            barrier.wait(timeout=10)
            return client.post(
                "/api/v1/orders/", payload, format="json", HTTP_IDEMPOTENCY_KEY=key
            ).status_code
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(checkout, u.pk) for u in [first, second]]
        statuses = sorted(f.result(timeout=20) for f in futures)
    assert statuses == ([200, 201] if same_customer else [201, 409])
    product.refresh_from_db()
    assert product.stock == 0 and Order.objects.count() == 1

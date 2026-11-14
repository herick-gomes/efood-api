from copy import deepcopy
from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from shop.models import Order, Product, Restaurant

pytestmark = pytest.mark.django_db
URL = "/api/v1/orders/"


def create(client, payload, key=None):
    return client.post(URL, payload, format="json", HTTP_IDEMPOTENCY_KEY=str(key or uuid4()))


def test_checkout_snapshot_and_server_total(client, payload, product, restaurant):
    response = create(client, payload)
    assert response.status_code == 201, response.data
    assert response.data["total"] == "51.00"
    assert response.data["payment_status"] == "simulated_approved"
    assert response.data["delivery"]["zip_code"] == "24000000"
    product.refresh_from_db()
    assert product.stock == 8
    product.price = "99.99"
    product.name = "Renamed"
    product.save()
    restaurant.name = "New kitchen"
    restaurant.save()
    order = client.get(URL + response.data["id"] + "/").data
    assert order["items"][0]["unit_price"] == "25.50"
    assert order["items"][0]["product_name"] == "Lunch bowl"
    assert order["restaurant_name"] == "Demo kitchen"


@pytest.mark.parametrize(
    "field,value",
    [
        ("total", "0.01"),
        ("customer", 99),
        ("payment", {"card": "fake"}),
        ("status", "delivered"),
        ("restaurant", 1),
    ],
)
def test_untrusted_fields_rejected(client, payload, field, value):
    payload[field] = value
    assert create(client, payload).status_code == 400
    assert Order.objects.count() == 0


@pytest.mark.parametrize("value", [0, -1, 51, "bad", 1.5])
def test_invalid_quantity(client, payload, value):
    payload["items"][0]["quantity"] = value
    assert create(client, payload).status_code == 400


def test_empty_or_duplicate_items(client, payload):
    original = deepcopy(payload["items"])
    payload["items"] = []
    assert create(client, payload).status_code == 400
    payload["items"] = original + original
    assert create(client, payload).status_code == 400


def test_item_price_rejected(client, payload):
    payload["items"][0]["price"] = "0.01"
    assert create(client, payload).status_code == 400


@pytest.mark.parametrize(
    "field,value", [("zip_code", "123"), ("receiver", ""), ("address", ""), ("number", ""), ("city", "")]
)
def test_bad_delivery(client, payload, field, value):
    payload["delivery"][field] = value
    assert create(client, payload).status_code == 400


def test_key_required(client, payload):
    assert client.post(URL, payload, format="json").status_code == 400
    assert client.post(URL, payload, format="json", HTTP_IDEMPOTENCY_KEY="nope").status_code == 400


def test_idempotent_retry_and_conflict(client, payload, product):
    key = uuid4()
    first = create(client, payload, key)
    second = create(client, payload, key)
    assert second.status_code == 200 and second.data["id"] == first.data["id"]
    assert second["Idempotency-Replayed"] == "true"
    assert Order.objects.count() == 1
    product.refresh_from_db()
    assert product.stock == 8
    payload["items"][0]["quantity"] = 1
    assert create(client, payload, key).status_code == 409


def test_replay_survives_price_and_availability_changes(client, payload, product):
    key = uuid4()
    first = create(client, payload, key)
    product.price = "100"
    product.is_available = False
    product.save()
    again = create(client, payload, key)
    assert again.status_code == 200 and again.data["total"] == first.data["total"]


def test_same_key_is_scoped_to_customer(client, other, payload):
    key = uuid4()
    assert create(client, payload, key).status_code == 201
    client.force_authenticate(user=other)
    assert create(client, payload, key).status_code == 201
    assert Order.objects.count() == 2


@pytest.mark.parametrize("changes", [{"stock": 1}, {"is_available": False}, {"is_active": False}])
def test_unavailable_product(client, payload, product, changes):
    for k, v in changes.items():
        setattr(product, k, v)
    product.save()
    assert create(client, payload).status_code == 409
    assert Order.objects.count() == 0


@pytest.mark.parametrize("field", ["is_open", "is_active"])
def test_closed_restaurant(client, payload, restaurant, field):
    setattr(restaurant, field, False)
    restaurant.save()
    assert create(client, payload).status_code == 409


def test_mixed_restaurants_and_missing_product(client, payload, merchant):
    restaurant = Restaurant.objects.create(owner=merchant, name="Second", category="Test")
    product = Product.objects.create(restaurant=restaurant, name="Other", price=5, stock=5)
    payload["items"].append({"product_id": product.pk, "quantity": 1})
    assert create(client, payload).status_code == 400
    payload["items"][1]["product_id"] = 99999
    assert create(client, payload).status_code == 400


def test_failure_does_not_debit_other_products(client, payload, product, restaurant):
    empty = Product.objects.create(restaurant=restaurant, name="Empty", price=5, stock=0)
    payload["items"].append({"product_id": empty.pk, "quantity": 1})
    assert create(client, payload).status_code == 409
    product.refresh_from_db()
    assert product.stock == 10
    assert Order.objects.count() == 0


def test_customer_only_sees_own_orders(client, other, payload):
    order = create(client, payload).data
    client.force_authenticate(user=other)
    assert client.get(URL).data["count"] == 0
    assert client.get(URL + order["id"] + "/").status_code == 404
    assert client.post(URL + order["id"] + "/cancel/").status_code == 404


def test_anonymous_cannot_order(payload):
    assert create(APIClient(), payload).status_code == 401


def test_customer_cancel_restock_once(client, payload, product):
    order = create(client, payload).data
    url = URL + order["id"] + "/cancel/"
    assert client.post(url).status_code == 200
    assert client.post(url).status_code == 200
    product.refresh_from_db()
    assert product.stock == 10
    order = Order.objects.get(pk=order["id"])
    assert order.payment_status == "simulated_voided"
    assert order.events.count() == 2


def test_cancel_with_payload_rejected(client, payload):
    order = create(client, payload).data
    assert (
        client.post(URL + order["id"] + "/cancel/", {"status": "delivered"}, format="json").status_code == 400
    )


def test_complete_merchant_flow(client, merchant_client, payload):
    order = create(client, payload).data
    url = "/api/v1/merchant/orders/" + order["id"] + "/transition/"
    for state in ["accepted", "preparing", "out_for_delivery", "delivered"]:
        response = merchant_client.post(url, {"status": state}, format="json")
        assert response.status_code == 200, response.data
    assert len(response.data["events"]) == 5
    assert merchant_client.post(url, {"status": "cancelled"}, format="json").status_code == 409
    assert client.post(URL + order["id"] + "/cancel/").status_code == 409


def test_invalid_transition_and_customer_cannot_accept(client, merchant_client, payload):
    order = create(client, payload).data
    url = "/api/v1/merchant/orders/" + order["id"] + "/transition/"
    assert merchant_client.post(url, {"status": "delivered"}, format="json").status_code == 409
    assert client.post(url, {"status": "accepted"}, format="json").status_code == 403
    assert merchant_client.post(url, {"status": "unknown"}, format="json").status_code == 400
    merchant_client.post(url, {"status": "accepted"}, format="json")
    assert client.post(URL + order["id"] + "/cancel/").status_code == 409
    assert merchant_client.post(url, {"status": "cancelled"}, format="json").status_code == 200


def test_order_cannot_be_edited_or_deleted(client, payload):
    order = create(client, payload).data
    url = URL + order["id"] + "/"
    assert client.patch(url, {"total": "0.01"}, format="json").status_code == 405
    assert client.delete(url).status_code == 405


def test_foreign_merchant_order_isolation(client, merchant_client, other, payload):
    order = create(client, payload).data
    other.role = "merchant"
    other.save()
    merchant_client.force_authenticate(user=other)
    assert merchant_client.get("/api/v1/merchant/orders/").data["count"] == 0
    assert merchant_client.get("/api/v1/merchant/orders/" + order["id"] + "/").status_code == 404
    assert (
        merchant_client.post(
            "/api/v1/merchant/orders/" + order["id"] + "/transition/", {"status": "accepted"}, format="json"
        ).status_code
        == 404
    )


def test_invalid_order_id_is_not_a_server_error(client):
    assert client.post("/api/v1/orders/not-a-uuid/cancel/").status_code == 404


def test_merchant_status_filter(client, merchant_client, payload):
    create(client, payload)
    assert merchant_client.get("/api/v1/merchant/orders/?status=placed").data["count"] == 1
    assert merchant_client.get("/api/v1/merchant/orders/?status=delivered").data["count"] == 0
    assert merchant_client.get("/api/v1/merchant/orders/?status=unknown").status_code == 400

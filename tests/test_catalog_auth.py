import pytest
from rest_framework.test import APIClient

from shop.models import Restaurant, User

pytestmark = pytest.mark.django_db


def test_public_catalog_and_legacy_numeric_contract(product):
    c = APIClient()
    data = c.get("/api/v1/restaurants/").data
    assert data["count"] == 1 and data["results"][0]["products"][0]["price"] == "25.50"
    legacy = c.get("/api/v1/legacy/restaurantes/").data
    assert isinstance(legacy, list)
    assert legacy[0]["cardapio"][0]["preco"] == 25.5
    assert set(legacy[0]) == {
        "id",
        "titulo",
        "destacado",
        "tipo",
        "avaliacao",
        "descricao",
        "capa",
        "cardapio",
    }
    assert c.get(f"/api/v1/legacy/restaurantes/{product.restaurant_id}/").data == legacy[0]


def test_hidden_products_and_restaurants(product, restaurant):
    c = APIClient()
    product.stock = 0
    product.save()
    assert c.get("/api/v1/restaurants/").data["results"][0]["products"] == []
    restaurant.is_active = False
    restaurant.save()
    assert c.get("/api/v1/restaurants/").data["count"] == 0


def test_merchant_ownership_and_create(client, merchant_client, merchant, other, restaurant, product):
    assert (
        client.post(
            "/api/v1/merchant/restaurants/", {"name": "Hack", "category": "Test"}, format="json"
        ).status_code
        == 403
    )
    foreign = Restaurant.objects.create(owner=other, name="Private", category="Test")
    assert merchant_client.get(f"/api/v1/merchant/restaurants/{foreign.pk}/").status_code == 404
    assert (
        merchant_client.post(
            "/api/v1/merchant/products/",
            {"restaurant": foreign.pk, "name": "Hack", "price": "5.00"},
            format="json",
        ).status_code
        == 400
    )
    response = merchant_client.post(
        "/api/v1/merchant/restaurants/", {"name": "New", "category": "Pizza"}, format="json"
    )
    assert response.status_code == 201
    assert Restaurant.objects.get(pk=response.data["id"]).owner == merchant
    assert (
        merchant_client.patch(
            f"/api/v1/merchant/restaurants/{restaurant.pk}/", {"owner": other.pk}, format="json"
        ).status_code
        == 400
    )
    assert (
        merchant_client.patch(
            f"/api/v1/merchant/products/{product.pk}/", {"price": "0"}, format="json"
        ).status_code
        == 400
    )


def test_soft_delete_and_product_move(merchant_client, merchant, restaurant, product):
    second = Restaurant.objects.create(owner=merchant, name="Second", category="Test")
    url = f"/api/v1/merchant/products/{product.pk}/"
    assert merchant_client.patch(url, {"restaurant": second.pk}, format="json").status_code == 400
    assert merchant_client.delete(url).status_code == 204
    product.refresh_from_db()
    assert not product.is_active
    assert merchant_client.delete(f"/api/v1/merchant/restaurants/{restaurant.pk}/").status_code == 204
    assert Restaurant.objects.filter(pk=restaurant.pk).exists()


def test_register_hashes_password_and_prevents_escalation():
    c = APIClient()
    payload = {"username": "new", "password": "SecurePassword!2026"}
    assert c.post("/api/v1/auth/register/", {**payload, "role": "merchant"}, format="json").status_code == 400
    assert c.post("/api/v1/auth/register/", {**payload, "is_staff": True}, format="json").status_code == 400
    response = c.post("/api/v1/auth/register/", payload, format="json")
    assert response.status_code == 201 and "password" not in response.data
    user = User.objects.get(username="new")
    assert user.role == "customer" and user.check_password(payload["password"])
    assert c.post("/api/v1/auth/register/", payload, format="json").status_code == 400


def test_weak_password_rejected():
    assert (
        APIClient()
        .post("/api/v1/auth/register/", {"username": "new", "password": "123"}, format="json")
        .status_code
        == 400
    )


def test_jwt_rotation_logout_and_me(customer):
    c = APIClient()
    login = c.post(
        "/api/v1/auth/token/",
        {"username": customer.username, "password": "Strong!Password2026"},
        format="json",
    )
    assert login.status_code == 200
    tokens = login.data
    c.credentials(HTTP_AUTHORIZATION="Bearer " + tokens["access"])
    assert c.get("/api/v1/auth/me/").data["role"] == "customer"
    refreshed = c.post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]}, format="json")
    assert refreshed.status_code == 200
    assert c.post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]}, format="json").status_code == 401
    assert (
        c.post("/api/v1/auth/logout/", {"refresh": refreshed.data["refresh"]}, format="json").status_code
        == 200
    )
    assert (
        c.post("/api/v1/auth/refresh/", {"refresh": refreshed.data["refresh"]}, format="json").status_code
        == 401
    )


def test_inactive_user_and_invalid_credentials(customer):
    c = APIClient()
    assert (
        c.post(
            "/api/v1/auth/token/", {"username": customer.username, "password": "wrong"}, format="json"
        ).status_code
        == 401
    )
    customer.is_active = False
    customer.save()
    assert (
        c.post(
            "/api/v1/auth/token/",
            {"username": customer.username, "password": "Strong!Password2026"},
            format="json",
        ).status_code
        == 401
    )


def test_auth_throttle():
    c = APIClient()
    for _ in range(10):
        c.post("/api/v1/auth/token/", {"username": "unknown", "password": "wrong"}, format="json")
    assert (
        c.post("/api/v1/auth/token/", {"username": "unknown", "password": "wrong"}, format="json").status_code
        == 429
    )


def test_cors_allowlist():
    c = APIClient()
    good = c.options(
        "/api/v1/orders/",
        HTTP_ORIGIN="http://localhost:3000",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,idempotency-key,content-type",
    )
    assert good["access-control-allow-origin"] == "http://localhost:3000"
    bad = c.options(
        "/api/v1/orders/", HTTP_ORIGIN="https://untrusted.invalid", HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST"
    )
    assert "access-control-allow-origin" not in bad

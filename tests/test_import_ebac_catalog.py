"""Safeguards for importing the original course catalog."""

import json
from pathlib import Path

import pytest
from django.conf import settings
from django.core.management import call_command

from shop.models import Product, Restaurant, User


@pytest.mark.django_db
def test_preview_is_read_only(capsys):
    call_command("import_ebac_catalog")
    result = capsys.readouterr().out

    assert "DRY RUN: 6 restaurants, 22 products" in result
    assert Restaurant.objects.count() == 0
    assert Product.objects.count() == 0
    assert not User.objects.filter(username="efood_legacy_import").exists()


@pytest.mark.django_db
def test_original_catalog_is_idempotent_and_preserves_existing_records(client):
    owner = User.objects.create_user(
        username="original_owner",
        password="Test-Password-2026",
        role=User.Role.MERCHANT,
    )
    original = Restaurant.objects.create(owner=owner, name="Bella Tavola Italiana", category="Already here")
    existing_dish = Product.objects.create(restaurant=original, name="Do not edit", price="23.50", stock=7)

    call_command("import_ebac_catalog", apply=True)
    assert Restaurant.objects.count() == 7
    assert Product.objects.count() == 23

    merchant = User.objects.get(username="efood_legacy_import")
    assert merchant.role == User.Role.MERCHANT
    assert not merchant.has_usable_password()
    assert merchant.restaurants.count() == 6
    assert Product.objects.filter(restaurant__owner=merchant).count() == 22

    imported = Product.objects.get(
        restaurant__owner=merchant,
        restaurant__name="Bella Tavola Italiana",
        name="Ravioli al Tartufo Nero",
    )
    assert imported.image_url.startswith("https://api-ebac.vercel.app/")
    imported.stock = 9
    imported.save(update_fields=["stock"])

    call_command("import_ebac_catalog", apply=True)
    assert Restaurant.objects.count() == 7
    assert Product.objects.count() == 23
    imported.refresh_from_db()
    existing_dish.refresh_from_db()
    original.refresh_from_db()
    assert imported.stock == 9
    assert existing_dish.stock == 7
    assert original.category == "Already here"

    response = client.get("/api/v1/legacy/restaurantes/")
    assert response.status_code == 200
    assert len(response.data) == 7


def test_bundled_catalog_retains_original_dish_ids_per_restaurant():
    path = Path(settings.BASE_DIR) / "shop" / "fixtures" / "ebac_restaurantes.json"
    catalog = json.loads(path.read_text(encoding="utf-8"))

    assert len(catalog) == 6
    assert sum(len(item["cardapio"]) for item in catalog) == 22
    assert len({item["titulo"] for item in catalog}) == 6
    assert catalog[0]["titulo"] == "Bella Tavola Italiana"

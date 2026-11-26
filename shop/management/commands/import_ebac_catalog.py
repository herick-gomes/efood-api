"""Import the original EBAC Efood catalog without touching existing data."""

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from shop.models import Product, Restaurant, User


FIXTURE = Path(settings.BASE_DIR) / "shop" / "fixtures" / "ebac_restaurantes.json"
IMPORT_USERNAME = "efood_legacy_import"


def read_catalog():
    try:
        catalog = json.loads(FIXTURE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CommandError("Unable to load the bundled EBAC catalog.") from exc

    if not isinstance(catalog, list) or not catalog:
        raise CommandError("The EBAC catalog must be a non-empty list.")

    names = set()
    for restaurant in catalog:
        if not isinstance(restaurant, dict):
            raise CommandError("Invalid restaurant entry.")
        for field in ("titulo", "tipo", "descricao", "capa", "destacado", "cardapio"):
            if field not in restaurant:
                raise CommandError(f"Missing restaurant field: {field}")
        name = restaurant["titulo"]
        if not isinstance(name, str) or not name or len(name) > 100 or name in names:
            raise CommandError("Duplicate or invalid restaurant name.")
        names.add(name)
        if (
            len(restaurant["tipo"]) > 60
            or len(restaurant["descricao"]) > 600
            or len(restaurant["capa"]) > 200
            or not isinstance(restaurant["cardapio"], list)
        ):
            raise CommandError(f"Invalid restaurant data for {name}.")

        dish_names = set()
        for product in restaurant["cardapio"]:
            for field in ("nome", "descricao", "porcao", "foto", "preco"):
                if field not in product:
                    raise CommandError(f"Missing product field: {field}")
            dish_name = product["nome"]
            if (
                not isinstance(dish_name, str)
                or not dish_name
                or dish_name in dish_names
                or len(dish_name) > 100
                or len(product["descricao"]) > 500
                or len(product["porcao"]) > 100
                or len(product["foto"]) > 200
                or not isinstance(product["preco"], (int, float))
                or product["preco"] <= 0
            ):
                raise CommandError(f"Invalid product in {name}.")
            dish_names.add(dish_name)

    return catalog


class Command(BaseCommand):
    help = "Restore the six original EBAC restaurants and their 22 products."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually import the catalog (default: validate/preview only).",
        )
        parser.add_argument(
            "--stock",
            type=int,
            default=30,
            help="Starting stock for new demo products (default 30).",
        )

    def handle(self, *args, **options):
        catalog = read_catalog()
        products_total = sum(len(restaurant["cardapio"]) for restaurant in catalog)
        stock = options["stock"]
        if stock < 1:
            raise CommandError("--stock must be at least 1.")

        if not options["apply"]:
            self.stdout.write(
                f"DRY RUN: {len(catalog)} restaurants, {products_total} products. "
                "Run with --apply to insert missing records."
            )
            return

        created_restaurants = 0
        created_products = 0
        with transaction.atomic():
            merchant, created = User.objects.get_or_create(
                username=IMPORT_USERNAME,
                defaults={
                    "password": "!",  # Django unusable password: no login access.
                    "role": User.Role.MERCHANT,
                    "is_active": True,
                },
            )
            if merchant.role != User.Role.MERCHANT:
                raise CommandError("Import account exists without the merchant role.")

            for entry in catalog:
                restaurant, is_new = Restaurant.objects.get_or_create(
                    owner=merchant,
                    name=entry["titulo"],
                    defaults={
                        "category": entry["tipo"],
                        "description": entry["descricao"],
                        "image_url": entry["capa"],
                        "is_open": True,
                        "is_active": True,
                        "featured": entry["destacado"],
                    },
                )
                created_restaurants += int(is_new)
                for dish in entry["cardapio"]:
                    _, is_new_product = Product.objects.get_or_create(
                        restaurant=restaurant,
                        name=dish["nome"],
                        defaults={
                            "description": dish["descricao"],
                            "portion": dish["porcao"],
                            "image_url": dish["foto"],
                            "price": str(dish["preco"]),
                            "stock": stock,
                            "is_available": True,
                            "is_active": True,
                        },
                    )
                    created_products += int(is_new_product)

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {created_restaurants} restaurants and "
                f"{created_products} products; all existing records left untouched."
            )
        )

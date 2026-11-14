import os
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from shop.models import Product, Restaurant, User


class Command(BaseCommand):
    help = "Create fictional customer, merchant and catalog for local demonstrations."

    @transaction.atomic
    def handle(self, *args, **kwargs):
        if not settings.DEBUG:
            raise CommandError("Demo data is only allowed with DJANGO_DEBUG=1.")
        password = os.getenv("EFOOD_DEMO_PASSWORD")
        if not password:
            raise CommandError("Set EFOOD_DEMO_PASSWORD first.")
        if User.objects.filter(username__in=["demo_customer", "demo_merchant"]).exists():
            raise CommandError("Demo accounts already exist. No existing data was changed.")
        User.objects.create_user(username="demo_customer", password=password)
        merchant = User.objects.create_user(username="demo_merchant", password=password, role="merchant")
        menus = [
            (
                "Quintal da Vila",
                "Brazilian",
                "Comfort food, made for a relaxed lunch.",
                [
                    ("Lunch bowl", "29.90", "Rice, beans, vegetables and grilled chicken.", "One person"),
                    ("Roasted vegetables", "19.50", "A seasonal vegetable selection.", "One person"),
                ],
            ),
            (
                "Forno da Esquina",
                "Pizza",
                "A small fictional pizzeria for the API demonstration.",
                [
                    ("Margherita", "45.00", "Tomato, cheese and basil.", "Eight slices"),
                    ("Mushroom pizza", "52.00", "Mushrooms, herbs and cheese.", "Eight slices"),
                ],
            ),
        ]
        for name, category, description, products in menus:
            restaurant = Restaurant.objects.create(
                owner=merchant, name=name, category=category, description=description
            )
            for title, price, detail, portion in products:
                Product.objects.create(
                    restaurant=restaurant,
                    name=title,
                    price=Decimal(price),
                    description=detail,
                    portion=portion,
                    stock=30,
                )
        self.stdout.write(
            self.style.SUCCESS(
                "Created demo_customer, demo_merchant, two fictional restaurants and four products. Password: the value you supplied in EFOOD_DEMO_PASSWORD."
            )
        )

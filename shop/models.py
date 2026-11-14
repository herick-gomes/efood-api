import uuid
from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        MERCHANT = "merchant", "Merchant"

    role = models.CharField(max_length=12, choices=Role.choices, default=Role.CUSTOMER)


class Restaurant(models.Model):
    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name="restaurants")
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=60)
    description = models.CharField(max_length=600, blank=True)
    image_url = models.URLField(blank=True)
    is_open = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


class Product(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=500, blank=True)
    portion = models.CharField(max_length=100, blank=True)
    image_url = models.URLField(blank=True)
    price = models.DecimalField(
        max_digits=9, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    stock = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["id"]
        constraints = [models.CheckConstraint(condition=Q(price__gt=0), name="product_positive_price")]

    def __str__(self):
        return self.name


class Order(models.Model):
    class Status(models.TextChoices):
        PLACED = "placed", "Placed"
        ACCEPTED = "accepted", "Accepted"
        PREPARING = "preparing", "Preparing"
        OUT_FOR_DELIVERY = "out_for_delivery", "Out for delivery"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(User, on_delete=models.PROTECT, related_name="orders")
    restaurant = models.ForeignKey(Restaurant, on_delete=models.PROTECT, related_name="orders")
    restaurant_name = models.CharField(max_length=100)
    idempotency_key = models.UUIDField()
    request_hash = models.CharField(max_length=64)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLACED)
    payment_status = models.CharField(max_length=20, default="simulated_approved", editable=False)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    delivery = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "id"]
        indexes = [
            models.Index(fields=["customer", "-created_at"]),
            models.Index(fields=["restaurant", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "idempotency_key"], name="one_order_per_customer_key"
            ),
            models.CheckConstraint(condition=Q(total__gt=0), name="order_positive_total"),
        ]


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    product_name = models.CharField(max_length=100)
    unit_price = models.DecimalField(max_digits=9, decimal_places=2)
    quantity = models.PositiveSmallIntegerField()
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0) & Q(unit_price__gt=0) & Q(line_total__gt=0),
                name="positive_order_item",
            )
        ]


class OrderEvent(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="events")
    actor = models.ForeignKey(User, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=Order.Status.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

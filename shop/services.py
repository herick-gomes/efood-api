import hashlib
import json
from decimal import Decimal
from uuid import UUID

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError

from .errors import Conflict
from .models import Order, OrderEvent, OrderItem, Product, Restaurant, User


@transaction.atomic
def place_order(*, customer, key, data):
    # Serialize this customer's submissions before checking the idempotency key.
    User.objects.select_for_update().get(pk=customer.pk)
    fingerprint = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    previous = Order.objects.filter(customer=customer, idempotency_key=key).first()
    if previous:
        if previous.request_hash != fingerprint:
            raise Conflict("This Idempotency-Key was already used with different items or delivery details.")
        return previous, False
    ids = [item["product_id"] for item in data["items"]]
    # Discover the restaurant first; then lock restaurant before products consistently.
    restaurant_ids = set(Product.objects.filter(pk__in=ids).values_list("restaurant_id", flat=True))
    if len(restaurant_ids) != 1:
        raise ValidationError("An order must contain products from exactly one restaurant.")
    restaurant = get_object_or_404(Restaurant.objects.select_for_update(), pk=next(iter(restaurant_ids)))
    if not restaurant.is_active or not restaurant.is_open:
        raise Conflict("This restaurant is not accepting orders.")
    products = {p.pk: p for p in Product.objects.select_for_update().filter(pk__in=ids).order_by("pk")}
    if len(products) != len(ids):
        raise ValidationError("One or more products do not exist.")
    total = Decimal("0.00")
    for item in data["items"]:
        product = products[item["product_id"]]
        if not product.is_active or not product.is_available or product.stock < item["quantity"]:
            raise Conflict(f"Product {product.pk} is unavailable or has insufficient stock.")
        total += product.price * item["quantity"]
    order = Order.objects.create(
        customer=customer,
        restaurant=restaurant,
        restaurant_name=restaurant.name,
        idempotency_key=key,
        request_hash=fingerprint,
        total=total,
        delivery=data["delivery"],
    )
    rows = []
    for item in data["items"]:
        product = products[item["product_id"]]
        rows.append(
            OrderItem(
                order=order,
                product=product,
                product_name=product.name,
                unit_price=product.price,
                quantity=item["quantity"],
                line_total=product.price * item["quantity"],
            )
        )
        product.stock -= item["quantity"]
    Product.objects.bulk_update(list(products.values()), ["stock"])
    OrderItem.objects.bulk_create(rows)
    OrderEvent.objects.create(order=order, actor=customer, status=Order.Status.PLACED)
    return order, True


NEXT = {
    Order.Status.PLACED: {Order.Status.ACCEPTED, Order.Status.CANCELLED},
    Order.Status.ACCEPTED: {Order.Status.PREPARING, Order.Status.CANCELLED},
    Order.Status.PREPARING: {Order.Status.OUT_FOR_DELIVERY},
    Order.Status.OUT_FOR_DELIVERY: {Order.Status.DELIVERED},
    Order.Status.DELIVERED: set(),
    Order.Status.CANCELLED: set(),
}


@transaction.atomic
def transition_order(*, order_id, actor, target, merchant=False):
    try:
        order_id = UUID(str(order_id))
    except ValueError:
        raise Http404
    qs = Order.objects.select_for_update(of=("self",))
    if merchant:
        qs = qs.filter(restaurant__owner=actor)
    else:
        qs = qs.filter(customer=actor)
    order = get_object_or_404(qs, pk=order_id)
    if not merchant and target != Order.Status.CANCELLED:
        raise PermissionDenied("Customers may only cancel placed orders.")
    if order.status == target:
        return order
    if not merchant and order.status != Order.Status.PLACED:
        raise Conflict("Only a placed order can be cancelled by its customer.")
    if target not in NEXT[order.status]:
        raise Conflict(f"Cannot transition from {order.status} to {target}.")
    if target == Order.Status.CANCELLED:
        items = list(order.items.all())
        products = {
            p.pk: p
            for p in Product.objects.select_for_update()
            .filter(pk__in=[i.product_id for i in items])
            .order_by("pk")
        }
        for item in items:
            products[item.product_id].stock += item.quantity
        Product.objects.bulk_update(list(products.values()), ["stock"])
        order.payment_status = "simulated_voided"
    order.status = target
    order.save(update_fields=["status", "payment_status", "updated_at"])
    OrderEvent.objects.create(order=order, actor=actor, status=target)
    return order

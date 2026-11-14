from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Order, OrderEvent, OrderItem, Product, Restaurant, User


class StrictMixin:
    """Reject unsupported fields, especially prices, ownership and payment/card payloads."""

    def to_internal_value(self, data):
        if isinstance(data, dict):
            unknown = set(data) - {k for k, v in self.fields.items() if not v.read_only}
            if unknown:
                raise serializers.ValidationError(
                    {"fields": f"Unsupported fields: {', '.join(sorted(unknown))}."}
                )
        return super().to_internal_value(data)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "role"]


class RegisterSerializer(StrictMixin, serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)

    class Meta:
        model = User
        fields = ["username", "password"]

    def validate(self, attrs):
        try:
            validate_password(attrs["password"], User(username=attrs["username"]))
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data, role=User.Role.CUSTOMER)


class ProductSerializer(StrictMixin, serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "id",
            "restaurant",
            "name",
            "description",
            "portion",
            "image_url",
            "price",
            "stock",
            "is_available",
            "is_active",
        ]
        read_only_fields = ["id"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        self.fields["restaurant"].queryset = (
            Restaurant.objects.filter(owner=request.user, is_active=True)
            if request and request.user.is_authenticated
            else Restaurant.objects.none()
        )

    def validate_restaurant(self, value):
        if self.instance and self.instance.restaurant_id != value.pk:
            raise serializers.ValidationError("Products cannot be moved between restaurants.")
        return value


class PublicProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "restaurant", "name", "description", "portion", "image_url", "price", "is_available"]


class RestaurantSerializer(StrictMixin, serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ["id", "name", "category", "description", "image_url", "is_open", "is_active", "featured"]
        read_only_fields = ["id", "featured"]


class PublicRestaurantSerializer(serializers.ModelSerializer):
    products = PublicProductSerializer(many=True, read_only=True)

    class Meta:
        model = Restaurant
        fields = ["id", "name", "category", "description", "image_url", "is_open", "featured", "products"]


class DeliverySerializer(StrictMixin, serializers.Serializer):
    receiver = serializers.CharField(max_length=100, min_length=2)
    address = serializers.CharField(max_length=200, min_length=3)
    city = serializers.CharField(max_length=100, min_length=2)
    zip_code = serializers.RegexField(r"^\d{5}-?\d{3}$")
    number = serializers.CharField(max_length=20)
    complement = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")

    def validate_zip_code(self, value):
        return value.replace("-", "")


class ItemInputSerializer(StrictMixin, serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, max_value=50)


class CheckoutSerializer(StrictMixin, serializers.Serializer):
    items = ItemInputSerializer(many=True, min_length=1, max_length=30)
    delivery = DeliverySerializer()

    def validate_items(self, value):
        ids = [item["product_id"] for item in value]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Each product must appear once; use quantity.")
        return sorted(value, key=lambda x: x["product_id"])


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["product_id", "product_name", "unit_price", "quantity", "line_total"]


class OrderEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderEvent
        fields = ["status", "created_at"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    events = OrderEventSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "restaurant",
            "restaurant_name",
            "status",
            "payment_status",
            "total",
            "delivery",
            "items",
            "events",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class TransitionSerializer(StrictMixin, serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Status.choices)

from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import redirect
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import generics, mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenBlacklistView, TokenObtainPairView, TokenRefreshView

from .models import Order, Product, Restaurant, User
from .serializers import (
    CheckoutSerializer,
    OrderSerializer,
    ProductSerializer,
    PublicRestaurantSerializer,
    RegisterSerializer,
    RestaurantSerializer,
    TransitionSerializer,
    UserSerializer,
)
from .services import place_order, transition_order


class IsMerchant(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.MERCHANT


class IsCustomer(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.CUSTOMER


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError:
            raise ValidationError("This username is not available.")


class LoginView(TokenObtainPairView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class RefreshView(TokenRefreshView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class LogoutView(TokenBlacklistView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


def public_catalog():
    return Restaurant.objects.filter(is_active=True).prefetch_related(
        Prefetch("products", queryset=Product.objects.filter(is_active=True, is_available=True, stock__gt=0))
    )


class CatalogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PublicRestaurantSerializer
    permission_classes = [AllowAny]
    queryset = Restaurant.objects.none()

    def get_queryset(self):
        return public_catalog()


class LockedCatalogMixin:
    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        with transaction.atomic():
            item = self.get_object()
            item.is_active = False
            item.save(update_fields=["is_active"])
            return Response(status=status.HTTP_204_NO_CONTENT)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()
        qs = super().get_queryset()
        if self.action in ["update", "partial_update", "destroy"]:
            qs = qs.select_for_update(of=("self",))
        return qs


class MerchantRestaurantViewSet(LockedCatalogMixin, viewsets.ModelViewSet):
    permission_classes = [IsMerchant]
    serializer_class = RestaurantSerializer
    queryset = Restaurant.objects.all()

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(owner=self.request.user) if self.request.user.is_authenticated else qs.none()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class MerchantProductViewSet(LockedCatalogMixin, viewsets.ModelViewSet):
    permission_classes = [IsMerchant]
    serializer_class = ProductSerializer
    queryset = Product.objects.select_related("restaurant").all()

    def get_queryset(self):
        qs = super().get_queryset()
        return (
            qs.filter(restaurant__owner=self.request.user)
            if self.request.user.is_authenticated
            else qs.none()
        )


class CustomerOrderViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsCustomer]
    queryset = Order.objects.prefetch_related("items", "events").all()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return self.queryset.none()
        return self.queryset.filter(customer=self.request.user)

    @extend_schema(
        request=CheckoutSerializer,
        responses={201: OrderSerializer, 200: OrderSerializer},
        parameters=[
            OpenApiParameter(
                "Idempotency-Key",
                OpenApiTypes.UUID,
                OpenApiParameter.HEADER,
                required=True,
                description="New UUID per checkout intent. Reuse unchanged on network retry.",
            )
        ],
    )
    def create(self, request, *args, **kwargs):
        try:
            key = UUID(request.headers.get("Idempotency-Key", ""))
        except (ValueError, AttributeError):
            raise ValidationError({"Idempotency-Key": "A valid UUID header is required."})
        data = CheckoutSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        order, created = place_order(customer=request.user, key=key, data=data.validated_data)
        return Response(
            OrderSerializer(order).data,
            status=201 if created else 200,
            headers={"Idempotency-Replayed": "false" if created else "true"},
        )

    @extend_schema(request=None, responses=OrderSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        if request.data:
            raise ValidationError("Cancellation does not accept a request body.")
        order = transition_order(order_id=pk, actor=request.user, target=Order.Status.CANCELLED)
        return Response(OrderSerializer(order).data)


class MerchantOrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsMerchant]
    queryset = Order.objects.prefetch_related("items", "events").all()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return self.queryset.none()
        qs = self.queryset.filter(restaurant__owner=self.request.user)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            if status_filter not in Order.Status.values:
                raise ValidationError({"status": "Unknown order status."})
            qs = qs.filter(status=status_filter)
        return qs

    @extend_schema(request=TransitionSerializer, responses=OrderSerializer)
    @action(detail=True, methods=["post"], url_path="transition")
    def transition(self, request, pk=None):
        data = TransitionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        order = transition_order(
            order_id=pk, actor=request.user, target=data.validated_data["status"], merchant=True
        )
        return Response(OrderSerializer(order).data)


class LegacyDishSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    foto = serializers.CharField()
    preco = serializers.FloatField()
    nome = serializers.CharField()
    descricao = serializers.CharField()
    porcao = serializers.CharField()


class LegacyRestaurantSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    titulo = serializers.CharField()
    destacado = serializers.BooleanField()
    tipo = serializers.CharField()
    avaliacao = serializers.FloatField()
    descricao = serializers.CharField()
    capa = serializers.CharField()
    cardapio = LegacyDishSerializer(many=True)


def legacy_data(restaurant):
    return {
        "id": restaurant.pk,
        "titulo": restaurant.name,
        "destacado": restaurant.featured,
        "tipo": restaurant.category,
        "avaliacao": 0.0,
        "descricao": restaurant.description,
        "capa": restaurant.image_url,
        "cardapio": [
            {
                "id": p.pk,
                "nome": p.name,
                "descricao": p.description,
                "porcao": p.portion,
                "foto": p.image_url,
                "preco": float(p.price),
            }
            for p in restaurant.products.all()
        ],
    }


class LegacyCatalogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only adapter for the existing Efood React catalog. 0 rating means unrated."""

    serializer_class = LegacyRestaurantSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    queryset = Restaurant.objects.none()

    def get_queryset(self):
        return public_catalog().filter(is_open=True)

    def list(self, request, *args, **kwargs):
        return Response([legacy_data(r) for r in self.get_queryset()])

    def retrieve(self, request, *args, **kwargs):
        return Response(legacy_data(self.get_object()))


def health(request):
    return JsonResponse({"status": "ok", "version": "1.0.0", "payments": "simulated"})


def index(request):
    return redirect("/api/docs/")

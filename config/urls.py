from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from shop import views

router = DefaultRouter()
router.register("restaurants", views.CatalogViewSet, basename="restaurant")
router.register("orders", views.CustomerOrderViewSet, basename="order")
router.register("merchant/restaurants", views.MerchantRestaurantViewSet, basename="merchant-restaurant")
router.register("merchant/products", views.MerchantProductViewSet, basename="merchant-product")
router.register("merchant/orders", views.MerchantOrderViewSet, basename="merchant-order")
router.register("legacy/restaurantes", views.LegacyCatalogViewSet, basename="legacy-restaurant")
urlpatterns = [
    path("", views.index),
    path("health/", views.health),
    path("admin/", admin.site.urls),
    path("api/v1/", include(router.urls)),
    path("api/v1/auth/register/", views.RegisterView.as_view()),
    path("api/v1/auth/token/", views.LoginView.as_view()),
    path("api/v1/auth/refresh/", views.RefreshView.as_view()),
    path("api/v1/auth/logout/", views.LogoutView.as_view()),
    path("api/v1/auth/me/", views.MeView.as_view()),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]

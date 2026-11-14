from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Order, OrderEvent, OrderItem, Product, Restaurant, User


@admin.register(User)
class AccountAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Efood role", {"fields": ("role",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Efood role", {"fields": ("role",)}),)


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# Operational writes must use the API to preserve locking and history.
admin.site.register([Restaurant, Product, Order, OrderItem, OrderEvent], ReadOnlyAdmin)

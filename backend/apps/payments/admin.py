from unfold.admin import ModelAdmin, TabularInline

from django.contrib import admin

from .models import Wallet, WalletTransaction


class TransactionInline(TabularInline):
    model = WalletTransaction
    extra = 0
    can_delete = False
    fields = ("created_at", "kind", "amount", "balance_after", "reference")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Wallet)
class WalletAdmin(ModelAdmin):
    list_display = ("user", "balance", "updated_at")
    search_fields = ("user__phone",)
    inlines = [TransactionInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
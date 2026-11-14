from django import forms
from django.contrib import admin, messages
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action, display

from .models import Vehicle, VehiclePhoto


class VehicleAdminForm(forms.ModelForm):
    """Validates moderation decisions made by staff."""

    class Meta:
        model = Vehicle
        fields = ("approval_status", "rejection_reason", "is_active")

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("approval_status")
        reason = (cleaned.get("rejection_reason") or "").strip()

        if status == Vehicle.ApprovalStatus.REJECTED and not reason:
            self.add_error(
                "rejection_reason", "Enter a reason when rejecting a vehicle."
            )

        cleaned["rejection_reason"] = (
            reason if status == Vehicle.ApprovalStatus.REJECTED else ""
        )
        return cleaned


class VehiclePhotoInline(TabularInline):
    model = VehiclePhoto
    extra = 0
    can_delete = False
    fields = ("preview", "position")
    readonly_fields = ("preview", "position")

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="Photo")
    def preview(self, obj):
        if not obj.pk:
            return "-"
        return format_html(
            '<a href="{0}" target="_blank" rel="noopener">'
            '<img src="{0}" alt="" style="max-height:120px;border-radius:8px">'
            "</a>",
            obj.image.url,
        )


@admin.register(Vehicle)
class VehicleAdmin(ModelAdmin):
    form = VehicleAdminForm
    list_display = (
        "title",
        "owner",
        "kind",
        "price_per_hour",
        "approval_badge",
        "is_active",
        "created_at",
    )
    list_filter = ("approval_status", "kind", "is_active")
    search_fields = ("title", "brand", "model_name", "owner__phone")
    ordering = ("-created_at",)
    list_per_page = 25
    inlines = [VehiclePhotoInline]
    actions = ["approve_selected"]
    readonly_fields = (
        "owner",
        "kind",
        "title",
        "brand",
        "model_name",
        "year",
        "description",
        "transmission",
        "fuel_type",
        "seats",
        "insurance_expiry",
        "price_per_hour",
        "price_per_day",
        "deposit",
        "daily_km_limit",
        "min_fuel_percent",
        "latitude",
        "longitude",
        "address",
        "created_at",
    )
    fieldsets = (
        ("Vehicle", {"fields": ("owner", "kind", "title", "brand", "model_name", "year", "description")}),
        ("Car details", {"fields": ("transmission", "fuel_type", "seats", "insurance_expiry")}),
        ("Pricing and rules", {"fields": ("price_per_hour", "price_per_day", "deposit", "daily_km_limit", "min_fuel_percent")}),
        ("Location", {"fields": ("address", "latitude", "longitude")}),
        ("Moderation", {"fields": ("approval_status", "rejection_reason", "is_active")}),
        ("Dates", {"fields": ("created_at",)}),
    )

    def has_add_permission(self, request):
        # Vehicles are created by owners through the app.
        return False

    @display(
        description="Status",
        ordering="approval_status",
        label={
            "Approved": "success",
            "Pending review": "warning",
            "Rejected": "danger",
        },
    )
    def approval_badge(self, obj):
        return obj.get_approval_status_display()

    @action(description="Approve selected vehicles")
    def approve_selected(self, request, queryset):
        approved = 0
        for vehicle in queryset:
            vehicle.approval_status = Vehicle.ApprovalStatus.APPROVED
            vehicle.rejection_reason = ""
            vehicle.save(
                update_fields=["approval_status", "rejection_reason", "updated_at"]
            )
            approved += 1
        self.message_user(
            request, f"{approved} vehicle(s) approved.", messages.SUCCESS
        )
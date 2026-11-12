from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import Booking


@admin.register(Booking)
class BookingAdmin(ModelAdmin):
    list_display = (
        "id",
        "vehicle",
        "renter",
        "status_badge",
        "start_at",
        "end_at",
        "total_paid",
    )
    list_filter = ("status",)
    search_fields = ("renter__phone", "vehicle__title")
    ordering = ("-created_at",)
    list_per_page = 25

    @display(
        description="Status",
        ordering="status",
        label={
            "Confirmed": "info",
            "In progress": "warning",
            "Completed": "success",
            "Cancelled": "danger",
        },
    )
    def status_badge(self, obj):
        return obj.get_status_display()

    # Bookings are read-only in the admin; they change through the API.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
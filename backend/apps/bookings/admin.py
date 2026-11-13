from django import forms
from django.contrib import admin, messages
from django.utils.html import format_html_join
from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import Booking, DamageReport
from .services import BookingError
from .trip_services import resolve_damage


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
        "deposit_status",
    )
    list_filter = ("status", "deposit_status")
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


class DamageReportForm(forms.ModelForm):
    class Meta:
        model = DamageReport
        fields = ("approved_amount", "resolution_note")

    def clean_approved_amount(self):
        value = self.cleaned_data["approved_amount"]
        report = self.instance
        if report.pk and report.status == DamageReport.Status.OPEN:
            remaining = report.booking.deposit_remaining
            if value < 0 or value > remaining:
                raise forms.ValidationError(
                    f"Enter an amount between 0 and {remaining}."
                )
        return value


@admin.register(DamageReport)
class DamageReportAdmin(ModelAdmin):
    form = DamageReportForm
    list_display = ("id", "booking", "claimed_amount", "status_badge", "created_at")
    list_filter = ("status",)
    ordering = ("-created_at",)
    fieldsets = (
        (
            "Claim",
            {
                "fields": (
                    "booking",
                    "description",
                    "claimed_amount",
                    "deposit_left",
                    "renter_response",
                    "photos_preview",
                )
            },
        ),
        ("Decision", {"fields": ("status", "approved_amount", "resolution_note")}),
    )

    def get_readonly_fields(self, request, obj=None):
        base = (
            "booking",
            "description",
            "claimed_amount",
            "deposit_left",
            "renter_response",
            "photos_preview",
            "status",
        )
        if obj is not None and obj.status != DamageReport.Status.OPEN:
            return base + ("approved_amount", "resolution_note")
        return base

    @display(
        description="Status",
        ordering="status",
        label={"Open": "warning", "Resolved": "success"},
    )
    def status_badge(self, obj):
        return obj.get_status_display()

    @admin.display(description="Deposit left to settle")
    def deposit_left(self, obj):
        return obj.booking.deposit_remaining

    @admin.display(description="Photos")
    def photos_preview(self, obj):
        photos = obj.booking.photos.all()
        return format_html_join(
            "",
            '<a href="{0}" target="_blank" rel="noopener" '
            'style="display:inline-block;margin:4px;text-align:center">'
            '<img src="{0}" alt="" style="height:110px;border-radius:8px"><br>'
            "<small>{1} / {2}</small></a>",
            ((photo.image.url, photo.phase, photo.angle) for photo in photos),
        )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        if obj.status != DamageReport.Status.OPEN:
            return
        try:
            resolve_damage(
                report_id=obj.pk,
                approved_amount=form.cleaned_data["approved_amount"],
                note=form.cleaned_data["resolution_note"],
            )
        except BookingError as exc:
            self.message_user(request, exc.message, messages.ERROR)
            return
        self.message_user(
            request, "The claim was resolved and the deposit settled.", messages.SUCCESS
        )
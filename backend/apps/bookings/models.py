import os
import uuid

from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import (
    DateTimeRangeField,
    RangeBoundary,
    RangeOperators,
)
from django.db import models
from django.db.models import F, Func, Q
from django.utils import timezone

# Statuses that occupy the vehicle. Cancelled and completed bookings do not.
BLOCKING_STATUSES = ["confirmed", "active"]


class TsTzRange(Func):
    function = "TSTZRANGE"
    output_field = DateTimeRangeField()


class Booking(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmed"
        ACTIVE = "active", "In progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class DepositStatus(models.TextChoices):
        NONE = "none", "No deposit"
        HELD = "held", "Held"
        RELEASED = "released", "Released"

    renter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="bookings",
    )
    vehicle = models.ForeignKey(
        "vehicles.Vehicle",
        on_delete=models.PROTECT,
        related_name="bookings",
    )
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.CONFIRMED
    )

    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    # end_at plus the buffer between bookings. This is the range the database protects.
    blocked_until = models.DateTimeField()
    hours = models.PositiveIntegerField()

    # Price snapshot: later changes to the vehicle never affect this booking.
    price_per_hour = models.PositiveIntegerField()
    price_per_day = models.PositiveIntegerField()
    rental_amount = models.BigIntegerField()
    deposit_amount = models.BigIntegerField()
    total_paid = models.BigIntegerField()

    terms_version = models.CharField(max_length=30)
    terms_accepted_at = models.DateTimeField()
    idempotency_key = models.CharField(max_length=64, null=True, blank=True)

    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.CharField(max_length=10, blank=True)
    cancel_reason = models.TextField(blank=True)
    cancellation_fee = models.BigIntegerField(default=0)
    refund_amount = models.BigIntegerField(default=0)
    platform_fee = models.BigIntegerField(default=0)

    # Trip data
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    start_fuel_percent = models.PositiveSmallIntegerField(null=True, blank=True)
    end_fuel_percent = models.PositiveSmallIntegerField(null=True, blank=True)
    late_minutes = models.PositiveIntegerField(default=0)
    late_fee = models.BigIntegerField(default=0)
    fuel_fee = models.BigIntegerField(default=0)
    damage_deduction = models.BigIntegerField(default=0)
    deposit_status = models.CharField(
        max_length=10,
        choices=DepositStatus.choices,
        default=DepositStatus.HELD,
    )
    deposit_release_at = models.DateTimeField(null=True, blank=True)
    last_extension_key = models.CharField(max_length=64, blank=True, default="")

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-start_at"]
        indexes = [
            models.Index(fields=["renter", "-start_at"], name="booking_renter_idx"),
            models.Index(fields=["vehicle", "start_at"], name="booking_vehicle_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_at__gt=F("start_at")),
                name="booking_end_after_start",
            ),
            models.CheckConstraint(
                condition=Q(blocked_until__gte=F("end_at")),
                name="booking_blocked_covers_end",
            ),
            # Two blocking bookings of the same vehicle can never overlap.
            ExclusionConstraint(
                name="booking_no_overlap",
                expressions=[
                    (
                        TsTzRange("start_at", "blocked_until", RangeBoundary()),
                        RangeOperators.OVERLAPS,
                    ),
                    ("vehicle", RangeOperators.EQUAL),
                ],
                condition=Q(status__in=BLOCKING_STATUSES),
            ),
            models.UniqueConstraint(
                fields=["renter", "idempotency_key"],
                condition=Q(idempotency_key__isnull=False),
                name="booking_idempotent_per_renter",
            ),
        ]

    def __str__(self):
        return f"Booking {self.pk}: {self.vehicle_id} ({self.status})"

    @property
    def deposit_remaining(self):
        """Deposit still held after fees and damage deductions."""
        return max(
            0,
            self.deposit_amount
            - self.late_fee
            - self.fuel_fee
            - self.damage_deduction,
        )


def inspection_photo_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        ext = ".jpg"
    return f"inspections/{instance.booking_id}/{instance.phase}-{uuid.uuid4().hex}{ext}"


class InspectionPhoto(models.Model):
    """A photo of the vehicle's condition at the start or end of a trip,
    or evidence attached to a damage report."""

    class Phase(models.TextChoices):
        START = "start", "Start of trip"
        END = "end", "End of trip"
        DAMAGE = "damage", "Damage report"

    class Angle(models.TextChoices):
        FRONT = "front", "Front"
        REAR = "rear", "Rear"
        LEFT = "left", "Left side"
        RIGHT = "right", "Right side"
        DASHBOARD = "dashboard", "Dashboard"
        DAMAGE = "damage", "Damage"

    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name="photos"
    )
    phase = models.CharField(max_length=10, choices=Phase.choices)
    angle = models.CharField(max_length=10, choices=Angle.choices)
    image = models.ImageField(upload_to=inspection_photo_path)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    taken_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["phase", "angle", "id"]
        constraints = [
            # Start and end photos: exactly one per angle.
            models.UniqueConstraint(
                fields=["booking", "phase", "angle"],
                condition=Q(phase__in=["start", "end"]),
                name="inspection_one_photo_per_angle",
            )
        ]

    def __str__(self):
        return f"{self.phase}/{self.angle} of booking {self.booking_id}"


class DamageReport(models.Model):
    """The owner's damage claim against the deposit, settled by staff."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"

    booking = models.OneToOneField(
        Booking, on_delete=models.CASCADE, related_name="damage_report"
    )
    description = models.TextField()
    claimed_amount = models.BigIntegerField()
    renter_response = models.TextField(blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.OPEN
    )
    approved_amount = models.BigIntegerField(default=0)
    resolution_note = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(claimed_amount__gt=0),
                name="damage_claim_positive",
            )
        ]

    def __str__(self):
        return f"Damage report for booking {self.booking_id} ({self.status})"
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
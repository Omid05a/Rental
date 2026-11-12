import os
import uuid

from django.conf import settings
from django.contrib.gis.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import F, Q
from django.utils import timezone

MAX_PHOTOS = 6


class Vehicle(models.Model):
    class Kind(models.TextChoices):
        CAR = "car", "Car"
        BIKE = "bike", "Bicycle"

    class ApprovalStatus(models.TextChoices):
        PENDING = "pending", "Pending review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    class Transmission(models.TextChoices):
        AUTOMATIC = "automatic", "Automatic"
        MANUAL = "manual", "Manual"

    class FuelType(models.TextChoices):
        GASOLINE = "gasoline", "Gasoline"
        DIESEL = "diesel", "Diesel"
        HYBRID = "hybrid", "Hybrid"
        ELECTRIC = "electric", "Electric"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vehicles",
    )
    kind = models.CharField(max_length=10, choices=Kind.choices)
    title = models.CharField(max_length=120)
    brand = models.CharField(max_length=60)
    model_name = models.CharField(max_length=60)
    year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1300), MaxValueValidator(1450)],
    )
    description = models.TextField(blank=True)

    # Car-only details (empty for bicycles)
    transmission = models.CharField(
        max_length=10, choices=Transmission.choices, blank=True
    )
    fuel_type = models.CharField(max_length=10, choices=FuelType.choices, blank=True)
    seats = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
    )
    insurance_expiry = models.DateField(null=True, blank=True)

    # Prices are whole Toman amounts
    price_per_hour = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price_per_day = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    deposit = models.PositiveIntegerField(default=0)

    # Rental rules
    daily_km_limit = models.PositiveIntegerField(null=True, blank=True)
    min_fuel_percent = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        default=25,
        validators=[MaxValueValidator(100)],
    )

    # Pickup and return location
    location = models.PointField(geography=True, srid=4326)
    address = models.CharField(max_length=255)
    pickup_radius_m = models.PositiveIntegerField(default=50)

    is_active = models.BooleanField(default=True)
    approval_status = models.CharField(
        max_length=10,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
    )
    rejection_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["approval_status", "is_active", "kind"],
                name="vehicle_public_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(price_per_hour__gt=0) & Q(price_per_day__gt=0),
                name="vehicle_prices_positive",
            ),
            models.CheckConstraint(
                condition=Q(price_per_day__lte=F("price_per_hour") * 24),
                name="vehicle_daily_not_above_24_hourly",
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_kind_display()})"

    @property
    def latitude(self):
        return self.location.y

    @property
    def longitude(self):
        return self.location.x


def vehicle_photo_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        ext = ".jpg"
    return f"vehicles/{instance.vehicle_id}/{uuid.uuid4().hex}{ext}"


class VehiclePhoto(models.Model):
    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.CASCADE, related_name="photos"
    )
    image = models.ImageField(upload_to=vehicle_photo_path)
    position = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return f"Photo {self.pk} of vehicle {self.vehicle_id}"
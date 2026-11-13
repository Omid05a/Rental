from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from .models import Booking, DamageReport, InspectionPhoto
from .pricing import (
    billable_late_minutes,
    cancellation_fee,
    fuel_fee_amount,
    late_fee_amount,
)
from .trips import required_angles

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}


class QuoteRequestSerializer(serializers.Serializer):
    vehicle = serializers.IntegerField(min_value=1)
    start_at = serializers.DateTimeField()
    end_at = serializers.DateTimeField()


class BookingCreateSerializer(QuoteRequestSerializer):
    accept_terms = serializers.BooleanField()
    terms_version = serializers.CharField(max_length=30)

    def validate_accept_terms(self, value):
        if value is not True:
            raise serializers.ValidationError("You must accept the terms to book.")
        return value


class CancelSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=300, required=False, allow_blank=True)


class LocationSerializer(serializers.Serializer):
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)


class StartTripSerializer(LocationSerializer):
    qr_code = serializers.CharField(max_length=60)
    fuel_percent = serializers.IntegerField(
        min_value=0, max_value=100, required=False, allow_null=True
    )


class EndTripSerializer(LocationSerializer):
    fuel_percent = serializers.IntegerField(
        min_value=0, max_value=100, required=False, allow_null=True
    )


class ExtendSerializer(serializers.Serializer):
    hours = serializers.IntegerField(min_value=1, max_value=24)


class TripPhotoSerializer(serializers.Serializer):
    image = serializers.ImageField()
    phase = serializers.ChoiceField(choices=InspectionPhoto.Phase.choices)
    angle = serializers.ChoiceField(choices=InspectionPhoto.Angle.choices)
    latitude = serializers.FloatField(
        required=False, allow_null=True, min_value=-90, max_value=90
    )
    longitude = serializers.FloatField(
        required=False, allow_null=True, min_value=-180, max_value=180
    )

    def validate_image(self, value):
        if value.size > MAX_UPLOAD_BYTES:
            raise serializers.ValidationError("File is too large (max 5 MB).")
        image_format = getattr(getattr(value, "image", None), "format", None)
        if image_format not in ALLOWED_IMAGE_FORMATS:
            raise serializers.ValidationError(
                "Only JPEG, PNG or WebP images are allowed."
            )
        return value


class DamageCreateSerializer(serializers.Serializer):
    description = serializers.CharField(max_length=1000)
    claimed_amount = serializers.IntegerField(min_value=1)


class DamageRespondSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=1000)


class BookingSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    vehicle = serializers.SerializerMethodField()
    counterpart = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()
    cancel_fee_now = serializers.SerializerMethodField()
    trip = serializers.SerializerMethodField()
    damage = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = (
            "id",
            "status",
            "role",
            "vehicle",
            "counterpart",
            "start_at",
            "end_at",
            "hours",
            "price_per_hour",
            "price_per_day",
            "rental_amount",
            "deposit_amount",
            "total_paid",
            "can_cancel",
            "cancel_fee_now",
            "cancelled_at",
            "cancelled_by",
            "cancel_reason",
            "cancellation_fee",
            "refund_amount",
            "started_at",
            "ended_at",
            "start_fuel_percent",
            "end_fuel_percent",
            "late_minutes",
            "late_fee",
            "fuel_fee",
            "damage_deduction",
            "deposit_status",
            "deposit_release_at",
            "trip",
            "damage",
            "created_at",
        )
        read_only_fields = fields

    def _user(self):
        return self.context["request"].user

    def _absolute(self, url):
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url

    def get_role(self, obj):
        return "renter" if obj.renter_id == self._user().id else "owner"

    def get_vehicle(self, obj):
        vehicle = obj.vehicle
        photos = list(vehicle.photos.all())
        cover = self._absolute(photos[0].image.url) if photos else None
        return {
            "id": vehicle.pk,
            "kind": vehicle.kind,
            "title": vehicle.title,
            "brand": vehicle.brand,
            "model_name": vehicle.model_name,
            "address": vehicle.address,
            "latitude": vehicle.latitude,
            "longitude": vehicle.longitude,
            "pickup_radius_m": vehicle.pickup_radius_m,
            "cover": cover,
        }

    def get_counterpart(self, obj):
        other = obj.vehicle.owner if obj.renter_id == self._user().id else obj.renter
        return {"first_name": other.first_name, "phone": other.phone}

    def get_can_cancel(self, obj):
        return (
            obj.status == Booking.Status.CONFIRMED
            and timezone.now() < obj.start_at
        )

    def get_cancel_fee_now(self, obj):
        if not self.get_can_cancel(obj) or obj.renter_id != self._user().id:
            return 0
        return cancellation_fee(
            rental_amount=obj.rental_amount,
            price_per_day=obj.price_per_day,
            start_at=obj.start_at,
            now=timezone.now(),
        )

    def _photos(self, obj, phase):
        return [
            {
                "angle": photo.angle,
                "image": self._absolute(photo.image.url),
                "taken_at": photo.taken_at,
            }
            for photo in obj.photos.all()
            if photo.phase == phase
        ]

    def get_trip(self, obj):
        now = timezone.now()
        is_renter = obj.renter_id == self._user().id
        required = required_angles(obj.vehicle.kind)
        start_photos = self._photos(obj, InspectionPhoto.Phase.START)
        end_photos = self._photos(obj, InspectionPhoto.Phase.END)
        opens_at = obj.start_at - timedelta(minutes=settings.TRIP_EARLY_START_MINUTES)

        late_fee_now = 0
        fuel_fee_now = 0
        if obj.status == Booking.Status.ACTIVE:
            minutes = billable_late_minutes(obj.end_at, now)
            late_fee_now = min(
                late_fee_amount(minutes, obj.price_per_hour), obj.deposit_amount
            )

        return {
            "required_angles": required,
            "start_photos": start_photos,
            "end_photos": end_photos,
            "start_photos_done": {p["angle"] for p in start_photos}.issuperset(required),
            "end_photos_done": {p["angle"] for p in end_photos}.issuperset(required),
            "start_window_opens_at": opens_at,
            "can_start": (
                is_renter
                and obj.status == Booking.Status.CONFIRMED
                and opens_at <= now <= obj.end_at
            ),
            "can_extend": is_renter and obj.status == Booking.Status.ACTIVE,
            "can_end": is_renter and obj.status == Booking.Status.ACTIVE,
            "late_fee_now": late_fee_now,
            "fuel_fee_now": fuel_fee_now,
            "needs_fuel": obj.vehicle.kind == "car",
            "can_report_damage": self._can_report(obj, now),
        }

    def _report(self, obj):
        # Reverse one-to-one access raises when no report exists.
        return getattr(obj, "damage_report", None)

    def _can_report(self, obj, now):
        return (
            obj.vehicle.owner_id == self._user().id
            and obj.status == Booking.Status.COMPLETED
            and obj.deposit_status == Booking.DepositStatus.HELD
            and obj.deposit_release_at is not None
            and now <= obj.deposit_release_at
            and self._report(obj) is None
            and obj.deposit_remaining > 0
        )

    def get_damage(self, obj):
        report = self._report(obj)
        if report is None:
            return None
        return {
            "description": report.description,
            "claimed_amount": report.claimed_amount,
            "renter_response": report.renter_response,
            "status": report.status,
            "approved_amount": report.approved_amount,
            "resolution_note": report.resolution_note,
            "created_at": report.created_at,
            "photos": self._photos(obj, InspectionPhoto.Phase.DAMAGE),
        }
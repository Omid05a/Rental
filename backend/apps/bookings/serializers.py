from django.utils import timezone
from rest_framework import serializers

from .models import Booking
from .pricing import cancellation_fee


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


class BookingSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    vehicle = serializers.SerializerMethodField()
    counterpart = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()
    cancel_fee_now = serializers.SerializerMethodField()

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
            "created_at",
        )
        read_only_fields = fields

    def _user(self):
        return self.context["request"].user

    def get_role(self, obj):
        return "renter" if obj.renter_id == self._user().id else "owner"

    def get_vehicle(self, obj):
        vehicle = obj.vehicle
        photos = list(vehicle.photos.all())
        request = self.context.get("request")
        cover = None
        if photos:
            url = photos[0].image.url
            cover = request.build_absolute_uri(url) if request else url
        return {
            "id": vehicle.pk,
            "kind": vehicle.kind,
            "title": vehicle.title,
            "brand": vehicle.brand,
            "model_name": vehicle.model_name,
            "address": vehicle.address,
            "latitude": vehicle.latitude,
            "longitude": vehicle.longitude,
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
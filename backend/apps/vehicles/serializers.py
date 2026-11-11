from django.contrib.gis.geos import Point
from django.utils import timezone
from rest_framework import serializers

from .models import Vehicle, VehiclePhoto

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}

CAR_ONLY_TEXT_FIELDS = ("transmission", "fuel_type")
CAR_ONLY_NUMBER_FIELDS = ("seats", "insurance_expiry", "min_fuel_percent")


class VehiclePhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehiclePhoto
        fields = ("id", "image", "position")
        read_only_fields = fields


class PhotoUploadSerializer(serializers.Serializer):
    image = serializers.ImageField()

    def validate_image(self, value):
        if value.size > MAX_UPLOAD_BYTES:
            raise serializers.ValidationError("File is too large (max 5 MB).")
        image_format = getattr(getattr(value, "image", None), "format", None)
        if image_format not in ALLOWED_IMAGE_FORMATS:
            raise serializers.ValidationError(
                "Only JPEG, PNG or WebP images are allowed."
            )
        return value


class DistanceMixin(serializers.Serializer):
    distance_m = serializers.SerializerMethodField()

    def get_distance_m(self, obj):
        # "distance" is annotated only when the request includes lat and lng.
        distance = getattr(obj, "distance", None)
        return round(distance.m) if distance is not None else None


class VehicleSerializer(DistanceMixin, serializers.ModelSerializer):
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    photos = VehiclePhotoSerializer(many=True, read_only=True)
    owner_first_name = serializers.CharField(
        source="owner.first_name", read_only=True
    )

    class Meta:
        model = Vehicle
        fields = (
            "id",
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
            "pickup_radius_m",
            "is_active",
            "approval_status",
            "rejection_reason",
            "photos",
            "owner_first_name",
            "distance_m",
        )
        read_only_fields = ("id", "approval_status", "rejection_reason")

    def validate(self, attrs):
        instance = self.instance

        def value(name):
            if name in attrs:
                return attrs[name]
            return getattr(instance, name, None) if instance else None

        kind = value("kind")
        if instance and kind != instance.kind:
            raise serializers.ValidationError(
                {"kind": "Vehicle type cannot be changed."}
            )

        errors = {}
        if kind == Vehicle.Kind.CAR:
            for name in ("transmission", "fuel_type", "seats"):
                if not value(name):
                    errors[name] = "This field is required for cars."
            expiry = value("insurance_expiry")
            if not expiry:
                errors["insurance_expiry"] = (
                    "Insurance expiry date is required for cars."
                )
            elif expiry < timezone.localdate():
                errors["insurance_expiry"] = "The insurance has expired."
        else:
            # Bicycles have no car-only details.
            for name in CAR_ONLY_TEXT_FIELDS:
                attrs[name] = ""
            for name in CAR_ONLY_NUMBER_FIELDS:
                attrs[name] = None

        hourly = value("price_per_hour")
        daily = value("price_per_day")
        if hourly and daily and daily > hourly * 24:
            errors["price_per_day"] = (
                "The daily price cannot exceed 24 times the hourly price."
            )

        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def create(self, validated_data):
        latitude = validated_data.pop("latitude")
        longitude = validated_data.pop("longitude")
        validated_data["location"] = Point(longitude, latitude, srid=4326)
        return Vehicle.objects.create(**validated_data)

    def update(self, instance, validated_data):
        latitude = validated_data.pop("latitude", None)
        longitude = validated_data.pop("longitude", None)
        if (latitude is None) != (longitude is None):
            raise serializers.ValidationError(
                {"latitude": "Send latitude and longitude together."}
            )
        if latitude is not None:
            instance.location = Point(longitude, latitude, srid=4326)
        return super().update(instance, validated_data)


class VehicleListSerializer(DistanceMixin, serializers.ModelSerializer):
    latitude = serializers.FloatField(read_only=True)
    longitude = serializers.FloatField(read_only=True)
    cover = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = (
            "id",
            "kind",
            "title",
            "brand",
            "model_name",
            "price_per_hour",
            "price_per_day",
            "latitude",
            "longitude",
            "address",
            "cover",
            "distance_m",
        )
        read_only_fields = fields

    def get_cover(self, obj):
        photos = list(obj.photos.all())
        if not photos:
            return None
        url = photos[0].image.url
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url
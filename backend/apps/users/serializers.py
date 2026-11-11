import re

from rest_framework import serializers

from .models import User

# Persian and Arabic-Indic digits mapped to ASCII digits
DIGIT_MAP = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
PHONE_RE = re.compile(r"^09\d{9}$")

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}


def normalize_digits(value):
    return value.translate(DIGIT_MAP).strip()


class PhoneField(serializers.CharField):
    def to_internal_value(self, data):
        value = normalize_digits(super().to_internal_value(data))
        if not PHONE_RE.match(value):
            raise serializers.ValidationError(
                "Enter a valid mobile number like 09123456789."
            )
        return value


class RequestOTPSerializer(serializers.Serializer):
    phone = PhoneField()


class VerifyOTPSerializer(serializers.Serializer):
    phone = PhoneField()
    code = serializers.CharField(max_length=6)

    def validate_code(self, value):
        return normalize_digits(value)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "phone",
            "first_name",
            "last_name",
            "verification_status",
            "rejection_reason",
        )
        read_only_fields = fields


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "phone",
            "first_name",
            "last_name",
            "verification_status",
            "rejection_reason",
        )
        read_only_fields = (
            "id",
            "phone",
            "verification_status",
            "rejection_reason",
        )


class DocumentUploadSerializer(serializers.Serializer):
    file = serializers.ImageField()

    def validate_file(self, value):
        if value.size > MAX_UPLOAD_BYTES:
            raise serializers.ValidationError("File is too large (max 5 MB).")
        image_format = getattr(getattr(value, "image", None), "format", None)
        if image_format not in ALLOWED_IMAGE_FORMATS:
            raise serializers.ValidationError(
                "Only JPEG, PNG or WebP images are allowed."
            )
        return value
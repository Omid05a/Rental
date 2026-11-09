import re

from rest_framework import serializers

from .models import User

# Persian and Arabic-Indic digits mapped to ASCII digits
DIGIT_MAP = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
PHONE_RE = re.compile(r"^09\d{9}$")


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
        fields = ("id", "phone", "first_name", "last_name", "verification_status")
        read_only_fields = fields


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "phone", "first_name", "last_name", "verification_status")
        read_only_fields = ("id", "phone", "verification_status")
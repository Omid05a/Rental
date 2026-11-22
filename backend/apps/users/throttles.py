from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle

from .serializers import normalize_digits


class OTPRequestIPThrottle(AnonRateThrottle):
    scope = "otp_request_ip"


class OTPVerifyIPThrottle(AnonRateThrottle):
    scope = "otp_verify_ip"


class _PhoneThrottle(SimpleRateThrottle):
    """Limits requests per phone number, regardless of the client IP."""

    def get_cache_key(self, request, view):
        # Normalize digits so "۰۹۱۲..." and "0912..." share one counter.
        phone = normalize_digits(str(request.data.get("phone", "")))
        if not phone:
            return None
        return self.cache_format % {"scope": self.scope, "ident": phone}


class OTPRequestPhoneThrottle(_PhoneThrottle):
    scope = "otp_request_phone"


class OTPVerifyPhoneThrottle(_PhoneThrottle):
    scope = "otp_verify_phone"
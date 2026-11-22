from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle


class OTPRequestIPThrottle(AnonRateThrottle):
    scope = "otp_request_ip"


class OTPVerifyIPThrottle(AnonRateThrottle):
    scope = "otp_verify_ip"


class _PhoneThrottle(SimpleRateThrottle):
    """Limits requests per phone number, regardless of the client IP."""

    def get_cache_key(self, request, view):
        phone = str(request.data.get("phone", "")).strip()
        if not phone:
            return None
        return self.cache_format % {"scope": self.scope, "ident": phone}


class OTPRequestPhoneThrottle(_PhoneThrottle):
    scope = "otp_request_phone"


class OTPVerifyPhoneThrottle(_PhoneThrottle):
    scope = "otp_verify_phone"
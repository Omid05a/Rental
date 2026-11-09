import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone

from .models import OTPCode

logger = logging.getLogger(__name__)


class OTPError(Exception):
    """Raised when an OTP request or verification fails."""

    def __init__(self, message, code):
        super().__init__(message)
        self.message = message
        self.code = code


def generate_code():
    return f"{secrets.randbelow(10**6):06d}"


def send_sms(phone, message):
    """Development SMS backend: writes the message to the server log.

    Replace this function with a real SMS provider later.
    """
    logger.warning("SMS to %s: %s", phone, message)


def create_otp(phone):
    now = timezone.now()
    last = OTPCode.objects.filter(phone=phone).first()
    if last and (now - last.created_at).total_seconds() < settings.OTP_RESEND_SECONDS:
        raise OTPError("Please wait before requesting a new code.", "too_many_requests")

    code = generate_code()
    OTPCode.objects.create(
        phone=phone,
        code_hash=make_password(code),
        expires_at=now + timedelta(seconds=settings.OTP_EXPIRY_SECONDS),
    )
    send_sms(phone, f"Rental verification code: {code}")
    return code


def verify_otp(phone, code):
    now = timezone.now()
    otp = OTPCode.objects.filter(phone=phone, is_used=False).first()
    if otp is None or otp.expires_at < now:
        raise OTPError("The code is invalid or expired.", "invalid_code")
    if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise OTPError("Too many attempts. Request a new code.", "too_many_attempts")

    otp.attempts += 1
    if not check_password(code, otp.code_hash):
        otp.save(update_fields=["attempts"])
        raise OTPError("The code is invalid or expired.", "invalid_code")

    otp.is_used = True
    otp.save(update_fields=["attempts", "is_used"])
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from .models import OTPCode, User


@patch("apps.users.otp.generate_code", return_value="123456")
class OTPLoginTests(APITestCase):
    phone = "09120000000"

    def post(self, url, data):
        return self.client.post(url, data, format="json")

    def test_request_otp_creates_code(self, mock_code):
        response = self.post("/api/auth/request-otp/", {"phone": self.phone})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(OTPCode.objects.filter(phone=self.phone).count(), 1)

    def test_invalid_phone_is_rejected(self, mock_code):
        response = self.post("/api/auth/request-otp/", {"phone": "12345"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_persian_digits_are_normalized(self, mock_code):
        response = self.post("/api/auth/request-otp/", {"phone": "۰۹۱۲۰۰۰۰۰۰۰"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(OTPCode.objects.filter(phone=self.phone).exists())

    def test_resend_too_soon_is_rejected(self, mock_code):
        self.post("/api/auth/request-otp/", {"phone": self.phone})
        response = self.post("/api/auth/request-otp/", {"phone": self.phone})
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_verify_creates_user_and_returns_tokens(self, mock_code):
        self.post("/api/auth/request-otp/", {"phone": self.phone})
        response = self.post(
            "/api/auth/verify-otp/", {"phone": self.phone, "code": "123456"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertTrue(response.data["is_new_user"])
        self.assertTrue(User.objects.filter(phone=self.phone).exists())

    def test_wrong_code_is_rejected(self, mock_code):
        self.post("/api/auth/request-otp/", {"phone": self.phone})
        response = self.post(
            "/api/auth/verify-otp/", {"phone": self.phone, "code": "000000"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(phone=self.phone).exists())

    def test_code_cannot_be_reused(self, mock_code):
        self.post("/api/auth/request-otp/", {"phone": self.phone})
        self.post("/api/auth/verify-otp/", {"phone": self.phone, "code": "123456"})
        response = self.post(
            "/api/auth/verify-otp/", {"phone": self.phone, "code": "123456"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
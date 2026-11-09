from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User


class ProfileTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone="09120000000")
        token = RefreshToken.for_user(self.user).access_token
        self.auth = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_profile_requires_authentication(self):
        response = self.client.get("/api/me/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_profile(self):
        response = self.client.get("/api/me/", **self.auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["phone"], "09120000000")

    def test_update_names(self):
        response = self.client.patch(
            "/api/me/",
            {"first_name": "Ali", "last_name": "Rezaei"},
            format="json",
            **self.auth,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Ali")
        self.assertEqual(self.user.last_name, "Rezaei")

    def test_phone_and_status_are_read_only(self):
        response = self.client.patch(
            "/api/me/",
            {"phone": "09129999999", "verification_status": "approved"},
            format="json",
            **self.auth,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, "09120000000")
        self.assertEqual(
            self.user.verification_status, User.VerificationStatus.NOT_SUBMITTED
        )
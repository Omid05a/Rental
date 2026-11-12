import io
import tempfile
from datetime import timedelta

from django.contrib.gis.geos import Point
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User

from .admin import VehicleAdminForm
from .models import Vehicle

TEHRAN = (35.6892, 51.3890)
NEAR_TEHRAN = (35.7000, 51.4000)
ISFAHAN = (32.6546, 51.6680)


def png_file(name="photo.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (20, 20), "white").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


def make_user(phone, verified=True):
    status = (
        User.VerificationStatus.APPROVED
        if verified
        else User.VerificationStatus.NOT_SUBMITTED
    )
    return User.objects.create_user(
        phone=phone, first_name="Ali", last_name="Rezaei", verification_status=status
    )


def auth_header(user):
    token = RefreshToken.for_user(user).access_token
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def make_vehicle(owner, coords=TEHRAN, **overrides):
    data = {
        "owner": owner,
        "kind": Vehicle.Kind.CAR,
        "title": "Peugeot 206",
        "brand": "Peugeot",
        "model_name": "206",
        "year": 1397,
        "transmission": "manual",
        "fuel_type": "gasoline",
        "seats": 5,
        "insurance_expiry": timezone.localdate() + timedelta(days=200),
        "price_per_hour": 100_000,
        "price_per_day": 900_000,
        "deposit": 5_000_000,
        "location": Point(coords[1], coords[0], srid=4326),
        "address": "Tehran",
        "approval_status": Vehicle.ApprovalStatus.APPROVED,
    }
    data.update(overrides)
    return Vehicle.objects.create(**data)


def car_payload(**extra):
    data = {
        "kind": "car",
        "title": "Peugeot 206",
        "brand": "Peugeot",
        "model_name": "206",
        "year": 1397,
        "transmission": "manual",
        "fuel_type": "gasoline",
        "seats": 5,
        "insurance_expiry": (timezone.localdate() + timedelta(days=200)).isoformat(),
        "price_per_hour": 100_000,
        "price_per_day": 900_000,
        "deposit": 5_000_000,
        "latitude": TEHRAN[0],
        "longitude": TEHRAN[1],
        "address": "Valiasr Sq, Tehran",
    }
    data.update(extra)
    return data


class OwnerApiTests(APITestCase):
    def setUp(self):
        # Store uploaded photos in a temporary folder.
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        override = override_settings(MEDIA_ROOT=tmp.name)
        override.enable()
        self.addCleanup(override.disable)

        self.owner = make_user("09120000000")
        self.auth = auth_header(self.owner)

    def create(self, payload, **kwargs):
        return self.client.post(
            "/api/my/vehicles/", payload, format="json", **(kwargs or self.auth)
        )

    def test_unverified_user_cannot_create(self):
        user = make_user("09130000000", verified=False)
        response = self.create(car_payload(), **auth_header(user))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "not_verified")

    def test_anonymous_cannot_create(self):
        response = self.client.post("/api/my/vehicles/", car_payload(), format="json")
        self.assertEqual(response.status_code, 401)

    def test_verified_user_creates_pending_car(self):
        response = self.create(car_payload())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["approval_status"], "pending")
        self.assertAlmostEqual(response.data["latitude"], TEHRAN[0], places=4)
        self.assertAlmostEqual(response.data["longitude"], TEHRAN[1], places=4)

    def test_car_requires_insurance_expiry(self):
        payload = car_payload()
        del payload["insurance_expiry"]
        response = self.create(payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("insurance_expiry", response.data)

    def test_expired_insurance_is_rejected(self):
        yesterday = (timezone.localdate() - timedelta(days=1)).isoformat()
        response = self.create(car_payload(insurance_expiry=yesterday))
        self.assertEqual(response.status_code, 400)
        self.assertIn("insurance_expiry", response.data)

    def test_year_accepts_solar_hijri(self):
        response = self.create(car_payload(year=1399))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["year"], 1399)

    def test_year_rejects_gregorian(self):
        response = self.create(car_payload(year=2018))
        self.assertEqual(response.status_code, 400)
        self.assertIn("year", response.data)

    def test_bike_ignores_car_only_fields(self):
        payload = car_payload(kind="bike", title="City bike")
        response = self.create(payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["transmission"], "")
        self.assertIsNone(response.data["seats"])
        self.assertIsNone(response.data["insurance_expiry"])

    def test_daily_price_cannot_exceed_24_hourly(self):
        response = self.create(
            car_payload(price_per_hour=10_000, price_per_day=300_000)
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("price_per_day", response.data)

    def test_database_rejects_daily_price_above_24_hourly(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                make_vehicle(self.owner, price_per_hour=10_000, price_per_day=300_000)

    def test_vehicle_type_cannot_change(self):
        vehicle = make_vehicle(self.owner)
        response = self.client.patch(
            f"/api/my/vehicles/{vehicle.pk}/",
            {"kind": "bike"},
            format="json",
            **self.auth,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("kind", response.data)

    def test_owner_can_update_price_and_location(self):
        vehicle = make_vehicle(self.owner)
        response = self.client.patch(
            f"/api/my/vehicles/{vehicle.pk}/",
            {
                "price_per_hour": 120_000,
                "latitude": NEAR_TEHRAN[0],
                "longitude": NEAR_TEHRAN[1],
            },
            format="json",
            **self.auth,
        )
        self.assertEqual(response.status_code, 200)
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.price_per_hour, 120_000)
        self.assertAlmostEqual(vehicle.latitude, NEAR_TEHRAN[0], places=4)

    def test_owner_cannot_change_approval_status(self):
        vehicle = make_vehicle(self.owner, approval_status="pending")
        self.client.patch(
            f"/api/my/vehicles/{vehicle.pk}/",
            {"approval_status": "approved"},
            format="json",
            **self.auth,
        )
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.approval_status, "pending")

    def test_other_user_cannot_edit_vehicle(self):
        vehicle = make_vehicle(self.owner)
        other = make_user("09140000000")
        response = self.client.patch(
            f"/api/my/vehicles/{vehicle.pk}/",
            {"title": "Hacked"},
            format="json",
            **auth_header(other),
        )
        self.assertEqual(response.status_code, 404)

    def test_my_vehicles_lists_only_own_including_pending(self):
        make_vehicle(self.owner, approval_status="pending")
        make_vehicle(make_user("09150000000"))
        response = self.client.get("/api/my/vehicles/", **self.auth)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_photo_upload_and_delete(self):
        vehicle = make_vehicle(self.owner)
        url = f"/api/my/vehicles/{vehicle.pk}/photos/"
        response = self.client.post(url, {"image": png_file()}, format="multipart", **self.auth)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(vehicle.photos.count(), 1)

        photo_id = response.data["id"]
        deleted = self.client.delete(f"{url}{photo_id}/", **self.auth)
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(vehicle.photos.count(), 0)

    def test_photo_upload_rejects_non_images(self):
        vehicle = make_vehicle(self.owner)
        fake = SimpleUploadedFile("x.png", b"not an image", content_type="image/png")
        response = self.client.post(
            f"/api/my/vehicles/{vehicle.pk}/photos/",
            {"image": fake},
            format="multipart",
            **self.auth,
        )
        self.assertEqual(response.status_code, 400)

    def test_photo_limit(self):
        vehicle = make_vehicle(self.owner)
        url = f"/api/my/vehicles/{vehicle.pk}/photos/"
        for _ in range(6):
            self.client.post(url, {"image": png_file()}, format="multipart", **self.auth)
        response = self.client.post(url, {"image": png_file()}, format="multipart", **self.auth)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "too_many_photos")


class PublicSearchTests(APITestCase):
    def setUp(self):
        self.owner = make_user("09120000000")

    def results(self, query=""):
        response = self.client.get(f"/api/vehicles/{query}")
        self.assertEqual(response.status_code, 200)
        return response.data["results"]

    def test_only_approved_and_active_vehicles_are_listed(self):
        shown = make_vehicle(self.owner)
        make_vehicle(self.owner, approval_status="pending")
        make_vehicle(self.owner, approval_status="rejected")
        make_vehicle(self.owner, is_active=False)
        ids = [item["id"] for item in self.results()]
        self.assertEqual(ids, [shown.pk])

    def test_filter_by_kind_and_price(self):
        make_vehicle(self.owner, title="Car", price_per_hour=200_000, price_per_day=1_500_000)
        make_vehicle(
            self.owner,
            title="Bike",
            kind="bike",
            transmission="",
            fuel_type="",
            seats=None,
            insurance_expiry=None,
            price_per_hour=20_000,
            price_per_day=150_000,
        )
        self.assertEqual([i["title"] for i in self.results("?kind=bike")], ["Bike"])
        self.assertEqual([i["title"] for i in self.results("?max_price=50000")], ["Bike"])
        self.assertEqual([i["title"] for i in self.results("?min_price=100000")], ["Car"])

    def test_nearby_search_filters_and_sorts_by_distance(self):
        far = make_vehicle(self.owner, coords=NEAR_TEHRAN, title="Near")
        make_vehicle(self.owner, coords=ISFAHAN, title="Isfahan")
        make_vehicle(self.owner, coords=TEHRAN, title="Closest")

        items = self.results(f"?lat={TEHRAN[0]}&lng={TEHRAN[1]}&radius_km=10")
        self.assertEqual([i["title"] for i in items], ["Closest", "Near"])
        self.assertLess(items[0]["distance_m"], items[1]["distance_m"])
        self.assertIsNotNone(far.pk)

    def test_invalid_query_returns_400(self):
        response = self.client.get("/api/vehicles/?lat=abc&lng=51")
        self.assertEqual(response.status_code, 400)
        response = self.client.get("/api/vehicles/?lat=35.7")
        self.assertEqual(response.status_code, 400)

    def test_detail_hides_unapproved_vehicle(self):
        pending = make_vehicle(self.owner, approval_status="pending")
        approved = make_vehicle(self.owner)
        self.assertEqual(self.client.get(f"/api/vehicles/{pending.pk}/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/vehicles/{approved.pk}/").status_code, 200)


class VehicleAdminFormTests(TestCase):
    def test_rejection_requires_reason(self):
        vehicle = make_vehicle(make_user("09120000000"))
        form = VehicleAdminForm(
            data={"approval_status": "rejected", "rejection_reason": "", "is_active": True},
            instance=vehicle,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("rejection_reason", form.errors)

    def test_approval_clears_reason(self):
        vehicle = make_vehicle(make_user("09120000000"))
        form = VehicleAdminForm(
            data={"approval_status": "approved", "rejection_reason": "old", "is_active": True},
            instance=vehicle,
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["rejection_reason"], "")
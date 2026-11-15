from datetime import timedelta

from django.utils import timezone

from apps.vehicles.test_api import NEAR_TEHRAN, auth_header

from .test_api import BookingTestCase


class VehicleEditTests(BookingTestCase):
    def patch(self, body, headers=None):
        return self.client.patch(
            f"/api/my/vehicles/{self.vehicle.pk}/",
            body,
            format="json",
            **(auth_header(self.owner) if headers is None else headers),
        )

    def approval(self):
        self.vehicle.refresh_from_db()
        return self.vehicle.approval_status

    def test_price_change_keeps_the_approval(self):
        response = self.patch({"price_per_hour": 120_000})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.approval(), "approved")

    def test_unchanged_values_keep_the_approval(self):
        response = self.patch({"title": "Peugeot 206", "address": "Tehran"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.approval(), "approved")

    def test_title_change_sends_the_vehicle_back_to_review(self):
        response = self.patch({"title": "Peugeot 206 SD"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["approval_status"], "pending")
        self.assertEqual(self.approval(), "pending")

    def test_description_change_sends_the_vehicle_back_to_review(self):
        self.patch({"description": "New text"})
        self.assertEqual(self.approval(), "pending")

    def test_moving_the_location_sends_the_vehicle_back_to_review(self):
        response = self.patch(
            {"latitude": NEAR_TEHRAN[0], "longitude": NEAR_TEHRAN[1]}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.approval(), "pending")

    def test_edited_rejected_vehicle_is_resubmitted(self):
        self.vehicle.approval_status = "rejected"
        self.vehicle.rejection_reason = "Blurry photo"
        self.vehicle.save()

        response = self.patch({"price_per_hour": 120_000})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["approval_status"], "pending")
        self.assertEqual(response.data["rejection_reason"], "")

    def test_toggling_active_does_not_resubmit_a_rejected_vehicle(self):
        self.vehicle.approval_status = "rejected"
        self.vehicle.rejection_reason = "Blurry photo"
        self.vehicle.save()

        response = self.patch({"is_active": False})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.approval(), "rejected")

    def test_toggling_active_works_with_an_expired_insurance(self):
        self.vehicle.insurance_expiry = timezone.localdate() - timedelta(days=3)
        self.vehicle.save()

        response = self.patch({"is_active": False})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.approval(), "approved")

    def test_a_new_expired_insurance_date_is_rejected(self):
        yesterday = (timezone.localdate() - timedelta(days=1)).isoformat()
        response = self.patch({"insurance_expiry": yesterday})
        self.assertEqual(response.status_code, 400)
        self.assertIn("insurance_expiry", response.data)

    def test_a_renewed_insurance_is_accepted(self):
        later = (timezone.localdate() + timedelta(days=300)).isoformat()
        response = self.patch({"insurance_expiry": later})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["insurance_expiry"], later)

    def test_location_lock_flag_is_reported_to_the_owner_only(self):
        url = f"/api/my/vehicles/{self.vehicle.pk}/"
        owner = auth_header(self.owner)
        self.assertFalse(self.client.get(url, **owner).data["location_locked"])

        self.book(self.now + timedelta(days=3))
        self.assertTrue(self.client.get(url, **owner).data["location_locked"])

        public = self.client.get(f"/api/vehicles/{self.vehicle.pk}/")
        self.assertFalse(public.data["location_locked"])
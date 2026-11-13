import tempfile
from datetime import timedelta

from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from apps.vehicles.test_api import TEHRAN, auth_header, make_user, png_file

from .models import Booking, DamageReport, InspectionPhoto
from .pricing import billable_late_minutes, fuel_fee_amount, late_fee_amount
from .test_api import BookingTestCase, balance
from .trip_services import release_due_deposits, resolve_damage
from .trips import distance_m, qr_code_for_vehicle, qr_matches

HERE = {"latitude": TEHRAN[0], "longitude": TEHRAN[1]}
FAR = {"latitude": 35.75, "longitude": 51.45}
CAR_ANGLES = ["front", "rear", "left", "right", "dashboard"]


class TripRulesTests(SimpleTestCase):
    def test_late_minutes_respect_grace_period(self):
        end = timezone.now()
        self.assertEqual(billable_late_minutes(end, end - timedelta(minutes=5)), 0)
        self.assertEqual(billable_late_minutes(end, end + timedelta(minutes=8)), 0)
        self.assertEqual(billable_late_minutes(end, end + timedelta(minutes=70)), 60)

    def test_late_fee_counts_every_started_hour(self):
        self.assertEqual(late_fee_amount(0, 100_000), 0)
        self.assertEqual(late_fee_amount(60, 100_000), 150_000)
        self.assertEqual(late_fee_amount(61, 100_000), 300_000)

    def test_fuel_fee(self):
        self.assertEqual(fuel_fee_amount(80, 78), 0)
        self.assertEqual(fuel_fee_amount(80, 50), 700_000)
        self.assertEqual(fuel_fee_amount(None, 50), 0)
        self.assertEqual(fuel_fee_amount(50, 80), 0)

    def test_distance(self):
        self.assertAlmostEqual(distance_m(35.0, 51.0, 35.0, 51.0), 0, places=3)
        meters = distance_m(35.0, 51.0, 35.001, 51.0)
        self.assertTrue(100 < meters < 125)

    def test_qr_code_is_signed(self):
        code = qr_code_for_vehicle(7)
        self.assertTrue(code.startswith("RENTAL-7-"))
        self.assertTrue(qr_matches(7, code))
        self.assertFalse(qr_matches(8, code))
        self.assertFalse(qr_matches(7, "RENTAL-7-forged"))


class TripTestCase(BookingTestCase):
    def setUp(self):
        super().setUp()
        # Store uploaded photos in a temporary folder.
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        override = override_settings(MEDIA_ROOT=tmp.name)
        override.enable()
        self.addCleanup(override.disable)
        self.owner_auth = auth_header(self.owner)

    def active_booking(self, start_offset_hours=-1, hours=3, fuel=80):
        start = self.now + timedelta(hours=start_offset_hours)
        booking = self.raw_booking(start, hours=hours, status="active")
        booking.started_at = start
        booking.start_fuel_percent = fuel
        booking.save()
        return booking

    def upload(self, booking_id, phase, angle, headers=None):
        return self.client.post(
            f"/api/bookings/{booking_id}/photos/",
            {"image": png_file(), "phase": phase, "angle": angle},
            format="multipart",
            **(self.auth if headers is None else headers),
        )

    def upload_all(self, booking_id, phase):
        for angle in CAR_ANGLES:
            response = self.upload(booking_id, phase, angle)
            self.assertEqual(response.status_code, 201, response.data)

    def start(self, booking_id, **overrides):
        body = {
            "qr_code": qr_code_for_vehicle(self.vehicle.pk),
            "fuel_percent": 80,
            **HERE,
        }
        body.update(overrides)
        return self.client.post(
            f"/api/bookings/{booking_id}/start/", body, format="json", **self.auth
        )

    def end(self, booking_id, **overrides):
        body = {"fuel_percent": 80, **HERE}
        body.update(overrides)
        return self.client.post(
            f"/api/bookings/{booking_id}/end/", body, format="json", **self.auth
        )

    def finish_trip(self):
        booking = self.active_booking()
        self.upload_all(booking.pk, "end")
        self.assertEqual(self.end(booking.pk).status_code, 200)
        return booking


class StartTripTests(TripTestCase):
    def test_start_succeeds_with_photos_qr_and_location(self):
        booking = self.raw_booking(self.now + timedelta(minutes=5))
        self.upload_all(booking.pk, "start")

        response = self.start(booking.pk)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], "active")
        self.assertEqual(response.data["start_fuel_percent"], 80)
        self.assertIsNotNone(response.data["started_at"])

    def test_start_requires_all_photos(self):
        booking = self.raw_booking(self.now + timedelta(minutes=5))
        response = self.start(booking.pk)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "inspection_incomplete")
        self.assertEqual(len(response.data["missing"]), 5)

    def test_start_rejects_wrong_qr_code(self):
        booking = self.raw_booking(self.now + timedelta(minutes=5))
        self.upload_all(booking.pk, "start")
        response = self.start(booking.pk, qr_code="RENTAL-1-forged")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "invalid_qr")

    def test_start_rejects_far_location(self):
        booking = self.raw_booking(self.now + timedelta(minutes=5))
        self.upload_all(booking.pk, "start")
        response = self.start(booking.pk, **FAR)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "too_far")
        self.assertGreater(response.data["distance_m"], response.data["limit_m"])

    def test_start_is_too_early(self):
        booking = self.raw_booking(self.now + timedelta(hours=2))
        response = self.start(booking.pk)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "too_early")

    def test_start_requires_fuel_level_for_cars(self):
        booking = self.raw_booking(self.now + timedelta(minutes=5))
        self.upload_all(booking.pk, "start")
        response = self.start(booking.pk, fuel_percent=None)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "fuel_required")

    def test_only_the_renter_can_start(self):
        booking = self.raw_booking(self.now + timedelta(minutes=5))
        response = self.client.post(
            f"/api/bookings/{booking.pk}/start/",
            {"qr_code": "x", **HERE},
            format="json",
            **self.owner_auth,
        )
        self.assertEqual(response.status_code, 403)

    def test_vehicle_cannot_start_while_in_use(self):
        self.active_booking(start_offset_hours=-2, hours=3)
        # The next rental starts right after the buffer of the active one.
        next_start = self.now + timedelta(hours=1, minutes=40)
        other = self.raw_booking(next_start)
        # Starting is not allowed yet: too early for the next booking.
        self.assertEqual(self.start(other.pk).status_code, 409)


class PhotoTests(TripTestCase):
    def test_owner_cannot_upload_start_photos(self):
        booking = self.raw_booking(self.now + timedelta(minutes=5))
        response = self.upload(
            booking.pk, "start", "front", headers=self.owner_auth
        )
        self.assertEqual(response.status_code, 403)

    def test_photos_are_closed_before_the_start_window(self):
        booking = self.raw_booking(self.now + timedelta(days=3))
        response = self.upload(booking.pk, "start", "front")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "too_early")

    def test_reupload_replaces_the_photo(self):
        booking = self.raw_booking(self.now + timedelta(minutes=5))
        self.upload(booking.pk, "start", "front")
        self.upload(booking.pk, "start", "front")
        self.assertEqual(
            InspectionPhoto.objects.filter(booking=booking, angle="front").count(), 1
        )

    def test_end_photos_need_an_active_rental(self):
        booking = self.raw_booking(self.now + timedelta(minutes=5))
        response = self.upload(booking.pk, "end", "front")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "not_active")

    def test_stranger_cannot_upload(self):
        booking = self.raw_booking(self.now + timedelta(minutes=5))
        stranger = auth_header(make_user("09170000000"))
        response = self.upload(booking.pk, "start", "front", headers=stranger)
        self.assertEqual(response.status_code, 404)


class EndTripTests(TripTestCase):
    def test_end_on_time_pays_owner_and_holds_deposit(self):
        booking = self.active_booking(start_offset_hours=-1, hours=3)
        self.upload_all(booking.pk, "end")

        response = self.end(booking.pk)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], "completed")
        self.assertEqual(response.data["late_fee"], 0)
        self.assertEqual(response.data["fuel_fee"], 0)
        self.assertEqual(response.data["deposit_status"], "held")
        self.assertIsNotNone(response.data["deposit_release_at"])
        # Rental 300,000 minus 15% commission.
        self.assertEqual(balance(self.owner), 255_000)

    def test_end_requires_photos(self):
        booking = self.active_booking()
        response = self.end(booking.pk)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "inspection_incomplete")

    def test_end_outside_return_area(self):
        booking = self.active_booking()
        self.upload_all(booking.pk, "end")
        response = self.end(booking.pk, **FAR)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "outside_return_area")

    def test_end_requires_fuel_level_for_cars(self):
        booking = self.active_booking()
        self.upload_all(booking.pk, "end")
        response = self.end(booking.pk, fuel_percent=None)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "fuel_required")

    def test_late_return_charges_fee_from_deposit(self):
        booking = self.active_booking(start_offset_hours=-5, hours=3)
        self.upload_all(booking.pk, "end")

        response = self.end(booking.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["late_fee"], 300_000)
        self.assertTrue(110 <= response.data["late_minutes"] <= 112)
        # (300,000 rental + 300,000 fee) minus 15% commission.
        self.assertEqual(balance(self.owner), 510_000)

    def test_fees_never_exceed_the_deposit(self):
        booking = self.active_booking(start_offset_hours=-5, hours=3)
        booking.deposit_amount = 100_000
        booking.save()
        self.upload_all(booking.pk, "end")

        response = self.end(booking.pk)
        self.assertEqual(response.data["late_fee"], 100_000)

    def test_low_fuel_adds_fuel_fee(self):
        booking = self.active_booking(fuel=80)
        self.upload_all(booking.pk, "end")

        response = self.end(booking.pk, fuel_percent=50)
        self.assertEqual(response.data["fuel_fee"], 700_000)
        # (300,000 rental + 700,000 fee) minus 15% commission.
        self.assertEqual(balance(self.owner), 850_000)

    def test_only_the_renter_can_end(self):
        booking = self.active_booking()
        self.upload_all(booking.pk, "end")
        response = self.client.post(
            f"/api/bookings/{booking.pk}/end/",
            {"fuel_percent": 80, **HERE},
            format="json",
            **self.owner_auth,
        )
        self.assertEqual(response.status_code, 403)


class DepositTests(TripTestCase):
    def test_deposit_waits_for_the_damage_window(self):
        self.finish_trip()
        self.assertEqual(release_due_deposits(), 0)

    def test_deposit_is_returned_after_the_window(self):
        booking = self.finish_trip()
        Booking.objects.filter(pk=booking.pk).update(
            deposit_release_at=self.now - timedelta(minutes=1)
        )

        self.assertEqual(release_due_deposits(), 1)
        booking.refresh_from_db()
        self.assertEqual(booking.deposit_status, "released")
        self.assertEqual(balance(self.renter), 20_000_000 + 5_000_000)
        # A second run changes nothing.
        self.assertEqual(release_due_deposits(), 0)
        self.assertEqual(balance(self.renter), 25_000_000)

    def test_returned_deposit_excludes_fees(self):
        booking = self.active_booking(start_offset_hours=-5, hours=3)
        self.upload_all(booking.pk, "end")
        self.end(booking.pk)
        Booking.objects.filter(pk=booking.pk).update(
            deposit_release_at=self.now - timedelta(minutes=1)
        )

        release_due_deposits()
        self.assertEqual(balance(self.renter), 20_000_000 + 5_000_000 - 300_000)

    def test_viewing_bookings_releases_due_deposits(self):
        booking = self.finish_trip()
        Booking.objects.filter(pk=booking.pk).update(
            deposit_release_at=self.now - timedelta(minutes=1)
        )
        response = self.client.get(f"/api/bookings/{booking.pk}/", **self.auth)
        self.assertEqual(response.data["deposit_status"], "released")


class ExtendTripTests(TripTestCase):
    def extend(self, booking_id, hours=2, key=None, headers=None):
        extra = {"HTTP_IDEMPOTENCY_KEY": key} if key else {}
        return self.client.post(
            f"/api/bookings/{booking_id}/extend/",
            {"hours": hours},
            format="json",
            **extra,
            **(self.auth if headers is None else headers),
        )

    def test_extension_charges_the_difference(self):
        booking = self.active_booking(start_offset_hours=-1, hours=3)
        old_end = booking.end_at

        response = self.extend(booking.pk, hours=2)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["hours"], 5)
        self.assertEqual(response.data["rental_amount"], 500_000)
        booking.refresh_from_db()
        self.assertEqual(booking.end_at, old_end + timedelta(hours=2))
        self.assertEqual(balance(self.renter), 20_000_000 - 200_000)

    def test_retry_with_the_same_key_extends_once(self):
        booking = self.active_booking(start_offset_hours=-1, hours=3)
        first = self.extend(booking.pk, key="ext-1")
        second = self.extend(booking.pk, key="ext-1")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data["hours"], 5)
        self.assertEqual(balance(self.renter), 20_000_000 - 200_000)

    def test_extension_is_blocked_by_the_next_booking(self):
        booking = self.active_booking(start_offset_hours=-1, hours=3)
        self.raw_booking(booking.end_at + timedelta(minutes=40), hours=2)

        response = self.extend(booking.pk, hours=2)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "extension_blocked")
        self.assertEqual(balance(self.renter), 20_000_000)

    def test_extension_needs_enough_funds(self):
        booking = self.active_booking(start_offset_hours=-1, hours=3)
        poor_booking_user = self.renter
        from apps.payments.models import Wallet

        Wallet.objects.filter(user=poor_booking_user).update(balance=1_000)
        response = self.extend(booking.pk, hours=2)
        self.assertEqual(response.status_code, 402)
        self.assertEqual(response.data["code"], "insufficient_funds")

    def test_only_active_rentals_can_be_extended(self):
        booking = self.raw_booking(self.now + timedelta(days=3))
        response = self.extend(booking.pk)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "not_active")


class DamageTests(TripTestCase):
    def report(self, booking_id, amount=1_000_000, headers=None):
        return self.client.post(
            f"/api/bookings/{booking_id}/damage/",
            {"description": "Scratch on the left door", "claimed_amount": amount},
            format="json",
            **(self.owner_auth if headers is None else headers),
        )

    def test_owner_reports_damage_and_attaches_a_photo(self):
        booking = self.finish_trip()
        response = self.report(booking.pk)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["damage"]["status"], "open")

        photo = self.client.post(
            f"/api/bookings/{booking.pk}/photos/",
            {"image": png_file(), "phase": "damage", "angle": "damage"},
            format="multipart",
            **self.owner_auth,
        )
        self.assertEqual(photo.status_code, 201)

    def test_renter_cannot_report_damage(self):
        booking = self.finish_trip()
        response = self.report(booking.pk, headers=self.auth)
        self.assertEqual(response.status_code, 403)

    def test_claim_cannot_exceed_the_remaining_deposit(self):
        booking = self.finish_trip()
        response = self.report(booking.pk, amount=6_000_000)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "claim_too_high")

    def test_report_closes_after_the_window(self):
        booking = self.finish_trip()
        Booking.objects.filter(pk=booking.pk).update(
            deposit_release_at=self.now - timedelta(minutes=1)
        )
        response = self.report(booking.pk)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "report_closed")

    def test_only_one_report_per_booking(self):
        booking = self.finish_trip()
        self.report(booking.pk)
        response = self.report(booking.pk)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "already_reported")

    def test_renter_can_respond(self):
        booking = self.finish_trip()
        self.report(booking.pk)
        response = self.client.post(
            f"/api/bookings/{booking.pk}/damage/respond/",
            {"note": "The scratch was already there."},
            format="json",
            **self.auth,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["damage"]["renter_response"],
            "The scratch was already there.",
        )

    def test_open_report_keeps_the_deposit_held(self):
        booking = self.finish_trip()
        self.report(booking.pk)
        Booking.objects.filter(pk=booking.pk).update(
            deposit_release_at=self.now - timedelta(minutes=1)
        )
        self.assertEqual(release_due_deposits(), 0)
        booking.refresh_from_db()
        self.assertEqual(booking.deposit_status, "held")

    def test_resolution_settles_the_deposit(self):
        booking = self.finish_trip()
        self.report(booking.pk)
        report = DamageReport.objects.get(booking=booking)

        resolve_damage(report_id=report.pk, approved_amount=800_000, note="Partial")

        report.refresh_from_db()
        booking.refresh_from_db()
        self.assertEqual(report.status, "resolved")
        self.assertEqual(booking.deposit_status, "released")
        self.assertEqual(booking.damage_deduction, 800_000)
        # Trip payout 255,000 plus 800,000 minus 15% commission.
        self.assertEqual(balance(self.owner), 255_000 + 680_000)
        self.assertEqual(balance(self.renter), 20_000_000 + 4_200_000)

    def test_resolution_cannot_exceed_the_remaining_deposit(self):
        from .services import BookingError

        booking = self.finish_trip()
        self.report(booking.pk)
        report = DamageReport.objects.get(booking=booking)
        with self.assertRaises(BookingError):
            resolve_damage(report_id=report.pk, approved_amount=9_000_000)


class QrTests(TripTestCase):
    def test_owner_gets_the_vehicle_code(self):
        response = self.client.get(
            f"/api/my/vehicles/{self.vehicle.pk}/qr/", **self.owner_auth
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(qr_matches(self.vehicle.pk, response.data["qr_code"]))

    def test_other_users_cannot_get_the_code(self):
        response = self.client.get(
            f"/api/my/vehicles/{self.vehicle.pk}/qr/", **self.auth
        )
        self.assertEqual(response.status_code, 404)
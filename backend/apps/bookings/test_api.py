from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.payments.models import Wallet, WalletTransaction
from apps.payments.services import apply_transaction
from apps.vehicles.test_api import auth_header, make_user, make_vehicle

from .models import Booking
from .terms import TERMS_VERSION


def fund(user, amount):
    apply_transaction(user, amount, WalletTransaction.Kind.TOPUP, reference="test")


def balance(user):
    return Wallet.objects.get(user=user).balance


class BookingTestCase(APITestCase):
    def setUp(self):
        self.owner = make_user("09120000000")
        self.renter = make_user("09130000000")
        self.vehicle = make_vehicle(self.owner)
        self.auth = auth_header(self.renter)
        self.now = timezone.now().replace(microsecond=0)
        fund(self.renter, 20_000_000)

    def payload(self, start, hours=5, **extra):
        data = {
            "vehicle": self.vehicle.pk,
            "start_at": start.isoformat(),
            "end_at": (start + timedelta(hours=hours)).isoformat(),
            "accept_terms": True,
            "terms_version": TERMS_VERSION,
        }
        data.update(extra)
        return data

    def book(self, start, hours=5, headers=None, **extra):
        return self.client.post(
            "/api/bookings/",
            self.payload(start, hours, **extra),
            format="json",
            **(self.auth if headers is None else headers),
        )

    def cancel(self, booking_id, headers=None):
        return self.client.post(
            f"/api/bookings/{booking_id}/cancel/",
            {},
            format="json",
            **(self.auth if headers is None else headers),
        )

    def raw_booking(self, start, hours=5, status="confirmed"):
        end = start + timedelta(hours=hours)
        return Booking.objects.create(
            renter=self.renter,
            vehicle=self.vehicle,
            status=status,
            start_at=start,
            end_at=end,
            blocked_until=end + timedelta(minutes=30),
            hours=hours,
            price_per_hour=100_000,
            price_per_day=900_000,
            rental_amount=hours * 100_000,
            deposit_amount=5_000_000,
            total_paid=hours * 100_000 + 5_000_000,
            terms_version=TERMS_VERSION,
            terms_accepted_at=self.now,
        )


class CreateBookingTests(BookingTestCase):
    def test_booking_charges_rental_and_deposit(self):
        response = self.book(self.now + timedelta(days=3))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "confirmed")
        self.assertEqual(response.data["rental_amount"], 500_000)
        self.assertEqual(response.data["total_paid"], 5_500_000)
        self.assertEqual(balance(self.renter), 20_000_000 - 5_500_000)

        kinds = set(
            WalletTransaction.objects.filter(wallet__user=self.renter).values_list(
                "kind", flat=True
            )
        )
        self.assertEqual(kinds, {"topup", "booking_charge", "deposit_hold"})

    def test_same_idempotency_key_charges_once(self):
        headers = {**self.auth, "HTTP_IDEMPOTENCY_KEY": "attempt-1"}
        start = self.now + timedelta(days=3)
        first = self.book(start, headers=headers)
        second = self.book(start, headers=headers)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(Booking.objects.count(), 1)
        self.assertEqual(balance(self.renter), 20_000_000 - 5_500_000)

    def test_insufficient_funds_rolls_everything_back(self):
        poor = make_user("09140000000")
        fund(poor, 1_000_000)
        response = self.book(self.now + timedelta(days=3), headers=auth_header(poor))

        self.assertEqual(response.status_code, 402)
        self.assertEqual(response.data["code"], "insufficient_funds")
        self.assertEqual(Booking.objects.count(), 0)
        self.assertEqual(balance(poor), 1_000_000)

    def test_overlapping_booking_is_rejected(self):
        start = self.now + timedelta(days=3)
        self.assertEqual(self.book(start).status_code, 201)

        other = make_user("09150000000")
        fund(other, 20_000_000)
        response = self.book(start + timedelta(hours=2), headers=auth_header(other))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "slot_taken")

    def test_buffer_between_bookings_is_enforced(self):
        start = self.now + timedelta(days=3)
        self.assertEqual(self.book(start, hours=5).status_code, 201)

        too_close = start + timedelta(hours=5, minutes=10)
        self.assertEqual(self.book(too_close).status_code, 409)

        after_buffer = start + timedelta(hours=5, minutes=30)
        self.assertEqual(self.book(after_buffer).status_code, 201)

    def test_database_rejects_overlapping_bookings(self):
        start = self.now + timedelta(days=3)
        self.raw_booking(start)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.raw_booking(start + timedelta(hours=2))

    def test_cancelled_booking_does_not_block_the_database(self):
        start = self.now + timedelta(days=3)
        self.raw_booking(start, status="cancelled")
        self.raw_booking(start)
        self.assertEqual(Booking.objects.count(), 2)

    def test_terms_must_be_accepted(self):
        response = self.book(self.now + timedelta(days=3), accept_terms=False)
        self.assertEqual(response.status_code, 400)
        self.assertIn("accept_terms", response.data)

    def test_outdated_terms_version_is_rejected(self):
        response = self.book(self.now + timedelta(days=3), terms_version="old")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "terms_outdated")

    def test_period_rules(self):
        cases = [
            (self.now - timedelta(hours=3), 5, "start_in_past"),
            (self.now + timedelta(days=3), 0.5, "duration_too_short"),
            (self.now + timedelta(days=3), 24 * 15, "duration_too_long"),
            (self.now + timedelta(days=100), 5, "too_far_ahead"),
        ]
        for start, hours, code in cases:
            response = self.book(start, hours=hours)
            self.assertEqual(response.status_code, 400, code)
            self.assertEqual(response.data["code"], code)

    def test_insurance_must_cover_the_rental(self):
        self.vehicle.insurance_expiry = timezone.localdate() + timedelta(days=1)
        self.vehicle.save()
        response = self.book(self.now + timedelta(days=3))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "insurance_expired")

    def test_owner_cannot_book_own_vehicle(self):
        response = self.book(
            self.now + timedelta(days=3), headers=auth_header(self.owner)
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "own_vehicle")

    def test_unverified_user_cannot_book(self):
        user = make_user("09160000000", verified=False)
        response = self.book(self.now + timedelta(days=3), headers=auth_header(user))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "not_verified")

    def test_unapproved_vehicle_cannot_be_booked(self):
        self.vehicle.approval_status = "pending"
        self.vehicle.save()
        response = self.book(self.now + timedelta(days=3))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["code"], "vehicle_not_found")


class QuoteAndTermsTests(BookingTestCase):
    def quote(self, start, hours=5):
        return self.client.post(
            "/api/bookings/quote/",
            {
                "vehicle": self.vehicle.pk,
                "start_at": start.isoformat(),
                "end_at": (start + timedelta(hours=hours)).isoformat(),
            },
            format="json",
            **self.auth,
        )

    def test_quote_returns_price_and_funds_state(self):
        response = self.quote(self.now + timedelta(days=3), hours=5)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["hours"], 5)
        self.assertEqual(response.data["rental_amount"], 500_000)
        self.assertEqual(response.data["total"], 5_500_000)
        self.assertTrue(response.data["enough_funds"])

    def test_quote_applies_daily_cap(self):
        response = self.quote(self.now + timedelta(days=3), hours=20)
        self.assertEqual(response.data["rental_amount"], 900_000)

    def test_quote_reports_taken_slot(self):
        start = self.now + timedelta(days=3)
        self.book(start)
        response = self.quote(start)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "slot_taken")

    def test_terms_are_public(self):
        response = self.client.get("/api/terms/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["version"], TERMS_VERSION)
        self.assertGreaterEqual(len(response.data["sections"]), 5)


class CancelBookingTests(BookingTestCase):
    def test_early_cancellation_refunds_everything_and_frees_the_slot(self):
        start = self.now + timedelta(days=3)
        booking_id = self.book(start).data["id"]

        response = self.cancel(booking_id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "cancelled")
        self.assertEqual(response.data["cancellation_fee"], 0)
        self.assertEqual(response.data["refund_amount"], 5_500_000)
        self.assertEqual(balance(self.renter), 20_000_000)

        # The same period can be booked again.
        self.assertEqual(self.book(start).status_code, 201)

    def test_late_cancellation_charges_fee_and_pays_owner(self):
        booking_id = self.book(self.now + timedelta(hours=5)).data["id"]

        response = self.cancel(booking_id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["cancellation_fee"], 250_000)
        self.assertEqual(response.data["refund_amount"], 5_250_000)
        self.assertEqual(balance(self.renter), 20_000_000 - 250_000)
        self.assertEqual(balance(self.owner), 212_500)
        self.assertEqual(Booking.objects.get(pk=booking_id).platform_fee, 37_500)

    def test_owner_cancellation_is_free_for_the_renter(self):
        booking_id = self.book(self.now + timedelta(hours=5)).data["id"]

        response = self.cancel(booking_id, headers=auth_header(self.owner))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["cancelled_by"], "owner")
        self.assertEqual(response.data["cancellation_fee"], 0)
        self.assertEqual(balance(self.renter), 20_000_000)

    def test_started_booking_cannot_be_cancelled(self):
        booking = self.raw_booking(self.now - timedelta(hours=1))
        response = self.cancel(booking.pk)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "already_started")

    def test_cancelling_twice_is_rejected(self):
        booking_id = self.book(self.now + timedelta(days=3)).data["id"]
        self.cancel(booking_id)
        response = self.cancel(booking_id)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "not_cancellable")
        self.assertEqual(balance(self.renter), 20_000_000)

    def test_stranger_cannot_see_or_cancel(self):
        booking_id = self.book(self.now + timedelta(days=3)).data["id"]
        stranger = auth_header(make_user("09170000000"))

        detail = self.client.get(f"/api/bookings/{booking_id}/", **stranger)
        self.assertEqual(detail.status_code, 404)
        self.assertEqual(self.cancel(booking_id, headers=stranger).status_code, 404)


class ListingTests(BookingTestCase):
    def test_list_by_role(self):
        self.book(self.now + timedelta(days=3))

        mine = self.client.get("/api/bookings/", **self.auth)
        self.assertEqual(len(mine.data), 1)
        self.assertEqual(mine.data[0]["role"], "renter")

        as_owner = self.client.get(
            "/api/bookings/?role=owner", **auth_header(self.owner)
        )
        self.assertEqual(len(as_owner.data), 1)
        self.assertEqual(as_owner.data[0]["role"], "owner")

        none = self.client.get("/api/bookings/?role=owner", **self.auth)
        self.assertEqual(len(none.data), 0)

    def test_busy_times_are_public_and_skip_cancelled(self):
        self.book(self.now + timedelta(days=3))
        self.raw_booking(self.now + timedelta(days=6), status="cancelled")

        response = self.client.get(f"/api/vehicles/{self.vehicle.pk}/busy/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
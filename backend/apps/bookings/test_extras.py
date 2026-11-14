from datetime import timedelta

from apps.vehicles.test_api import NEAR_TEHRAN, TEHRAN, auth_header

from .test_trips import TripTestCase


class EarningsTests(TripTestCase):
    def earnings(self, headers=None):
        response = self.client.get(
            "/api/earnings/", **(self.owner_auth if headers is None else headers)
        )
        self.assertEqual(response.status_code, 200)
        return response.data

    def test_earnings_require_authentication(self):
        self.assertEqual(self.client.get("/api/earnings/").status_code, 401)

    def test_finished_trip_counts_net_of_commission(self):
        self.finish_trip()
        data = self.earnings()
        self.assertEqual(data["trips"], 1)
        self.assertEqual(data["total_gross"], 300_000)
        self.assertEqual(data["total_fees"], 45_000)
        self.assertEqual(data["total_net"], 255_000)
        self.assertEqual(data["items"][0]["kind"], "trip")
        self.assertEqual(data["by_vehicle"][0]["net"], 255_000)

    def test_late_cancellation_fee_counts_as_income(self):
        booking_id = self.book(self.now + timedelta(hours=5)).data["id"]
        self.cancel(booking_id)
        data = self.earnings()
        self.assertEqual(data["cancellations"], 1)
        self.assertEqual(data["total_gross"], 250_000)
        self.assertEqual(data["total_net"], 212_500)

    def test_free_cancellation_earns_nothing(self):
        booking_id = self.book(self.now + timedelta(days=3)).data["id"]
        self.cancel(booking_id)
        self.assertEqual(self.earnings()["total_net"], 0)

    def test_totals_add_up_and_pending_is_reported(self):
        self.finish_trip()
        cancelled = self.book(self.now + timedelta(hours=5)).data["id"]
        self.cancel(cancelled)
        self.book(self.now + timedelta(days=3))

        data = self.earnings()
        self.assertEqual(data["total_net"], 255_000 + 212_500)
        self.assertEqual(len(data["items"]), 2)
        self.assertEqual(data["pending_gross"], 500_000)

    def test_renter_has_no_earnings(self):
        self.finish_trip()
        data = self.earnings(headers=self.auth)
        self.assertEqual(data["total_net"], 0)
        self.assertEqual(data["items"], [])


class LocationLockTests(TripTestCase):
    def patch(self, body):
        return self.client.patch(
            f"/api/my/vehicles/{self.vehicle.pk}/",
            body,
            format="json",
            **auth_header(self.owner),
        )

    def test_location_cannot_move_while_a_booking_is_open(self):
        self.book(self.now + timedelta(days=3))
        response = self.patch(
            {"latitude": NEAR_TEHRAN[0], "longitude": NEAR_TEHRAN[1]}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("latitude", response.data)

    def test_same_location_and_other_fields_stay_editable(self):
        self.book(self.now + timedelta(days=3))
        same = self.patch({"latitude": TEHRAN[0], "longitude": TEHRAN[1]})
        self.assertEqual(same.status_code, 200)
        price = self.patch({"price_per_hour": 120_000})
        self.assertEqual(price.status_code, 200)

    def test_location_can_move_after_the_booking_is_cancelled(self):
        booking_id = self.book(self.now + timedelta(days=3)).data["id"]
        self.cancel(booking_id)
        response = self.patch(
            {"latitude": NEAR_TEHRAN[0], "longitude": NEAR_TEHRAN[1]}
        )
        self.assertEqual(response.status_code, 200)
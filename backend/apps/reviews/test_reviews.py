from datetime import timedelta

from apps.bookings.models import Booking
from apps.bookings.test_trips import TripTestCase
from apps.notifications.models import Notification

from .models import Review


class ReviewTestCase(TripTestCase):
    def review(self, booking_id, rating=5, comment="Great", headers=None):
        return self.client.post(
            f"/api/bookings/{booking_id}/review/",
            {"rating": rating, "comment": comment},
            format="json",
            **(self.auth if headers is None else headers),
        )

    def state(self, booking_id, headers=None):
        response = self.client.get(
            f"/api/bookings/{booking_id}/review/",
            **(self.auth if headers is None else headers),
        )
        self.assertEqual(response.status_code, 200)
        return response.data


class ReviewRulesTests(ReviewTestCase):
    def test_renter_reviews_the_owner_after_the_trip(self):
        booking = self.finish_trip()
        before = self.state(booking.pk)
        self.assertTrue(before["can_review"])

        response = self.review(booking.pk, rating=4, comment="Clean car")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["mine"]["rating"], 4)
        self.assertFalse(response.data["can_review"])

        review = Review.objects.get(booking=booking)
        self.assertEqual(review.subject_id, self.owner.pk)
        self.assertEqual(review.direction, "renter_to_owner")

    def test_trip_must_be_completed(self):
        booking = self.raw_booking(self.now + timedelta(days=3))
        response = self.review(booking.pk)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "not_completed")

    def test_one_review_per_author(self):
        booking = self.finish_trip()
        self.review(booking.pk)
        response = self.review(booking.pk)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "already_reviewed")

    def test_rating_must_be_between_one_and_five(self):
        booking = self.finish_trip()
        self.assertEqual(self.review(booking.pk, rating=0).status_code, 400)
        self.assertEqual(self.review(booking.pk, rating=6).status_code, 400)

    def test_outsiders_cannot_review_or_read(self):
        from apps.vehicles.test_api import auth_header, make_user

        booking = self.finish_trip()
        stranger = auth_header(make_user("09190000000"))
        self.assertEqual(self.review(booking.pk, headers=stranger).status_code, 404)
        response = self.client.get(
            f"/api/bookings/{booking.pk}/review/", **stranger
        )
        self.assertEqual(response.status_code, 404)

    def test_review_period_ends(self):
        booking = self.finish_trip()
        Booking.objects.filter(pk=booking.pk).update(
            ended_at=self.now - timedelta(days=15)
        )
        response = self.review(booking.pk)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "review_closed")
        self.assertFalse(self.state(booking.pk)["can_review"])


class BlindRevealTests(ReviewTestCase):
    def test_other_review_stays_hidden_until_you_write_yours(self):
        booking = self.finish_trip()
        self.review(booking.pk, rating=5)

        owner_view = self.state(booking.pk, headers=self.owner_auth)
        self.assertIsNone(owner_view["mine"])
        self.assertIsNone(owner_view["theirs"])

        response = self.review(booking.pk, rating=3, headers=self.owner_auth)
        self.assertEqual(response.data["theirs"]["rating"], 5)

        renter_view = self.state(booking.pk)
        self.assertEqual(renter_view["theirs"]["rating"], 3)

    def test_other_review_is_revealed_when_the_period_ends(self):
        booking = self.finish_trip()
        self.review(booking.pk, rating=5)
        Booking.objects.filter(pk=booking.pk).update(
            ended_at=self.now - timedelta(days=15)
        )
        owner_view = self.state(booking.pk, headers=self.owner_auth)
        self.assertEqual(owner_view["theirs"]["rating"], 5)

    def test_receiver_is_notified_without_the_rating_text(self):
        booking = self.finish_trip()
        self.review(booking.pk, rating=1, comment="Terrible")
        item = Notification.objects.get(user=self.owner, kind="review")
        self.assertNotIn("Terrible", item.body)
        self.assertEqual(item.link, f"/bookings/{booking.pk}")


class PublicRatingTests(ReviewTestCase):
    def test_vehicle_reviews_list_only_renter_reviews(self):
        booking = self.finish_trip()
        self.review(booking.pk, rating=5, comment="Great owner")
        self.review(booking.pk, rating=2, comment="Late renter", headers=self.owner_auth)

        response = self.client.get(f"/api/vehicles/{self.vehicle.pk}/reviews/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["avg"], 5.0)
        self.assertEqual(response.data["results"][0]["comment"], "Great owner")
        self.assertEqual(response.data["results"][0]["author_first_name"], "Ali")

    def test_ratings_for_many_vehicles(self):
        booking = self.finish_trip()
        self.review(booking.pk, rating=4)

        response = self.client.get(
            f"/api/reviews/vehicles/?ids={self.vehicle.pk},999999,abc"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.data), [str(self.vehicle.pk)])
        self.assertEqual(response.data[str(self.vehicle.pk)]["avg"], 4.0)
        self.assertEqual(response.data[str(self.vehicle.pk)]["count"], 1)

    def test_counterpart_rating_in_review_state(self):
        booking = self.finish_trip()
        self.review(booking.pk, rating=5)

        renter_view = self.state(booking.pk)
        self.assertEqual(renter_view["counterpart_rating"]["avg"], 5.0)
        self.assertEqual(renter_view["counterpart_rating"]["count"], 1)

        owner_view = self.state(booking.pk, headers=self.owner_auth)
        self.assertEqual(owner_view["counterpart_rating"]["count"], 0)
        self.assertIsNone(owner_view["counterpart_rating"]["avg"])

    def test_public_list_includes_average_rating(self):
        booking = self.finish_trip()
        self.review(booking.pk, rating=4)

        response = self.client.get("/api/vehicles/")
        item = next(i for i in response.data["results"] if i["id"] == self.vehicle.pk)
        self.assertEqual(item["rating_avg"], 4.0)
        self.assertEqual(item["rating_count"], 1)

    def test_unrated_vehicle_has_no_average(self):
        response = self.client.get("/api/vehicles/")
        item = next(i for i in response.data["results"] if i["id"] == self.vehicle.pk)
        self.assertIsNone(item["rating_avg"])
        self.assertEqual(item["rating_count"], 0)
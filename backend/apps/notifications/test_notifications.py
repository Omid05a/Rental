from datetime import timedelta

from django.utils import timezone

from apps.bookings.models import Booking
from apps.bookings.test_trips import TripTestCase
from apps.users.models import User
from apps.vehicles.models import Vehicle
from apps.vehicles.test_api import auth_header, make_user, make_vehicle

from .models import Notification


def dedupe_keys(user):
    return set(
        Notification.objects.filter(user=user).values_list("dedupe_key", flat=True)
    )


class NotificationApiTests(TripTestCase):
    def get(self, url, headers=None):
        return self.client.get(url, **(self.auth if headers is None else headers))

    def test_list_requires_authentication(self):
        self.assertEqual(self.client.get("/api/notifications/").status_code, 401)

    def test_booking_notifies_the_owner(self):
        response = self.book(self.now + timedelta(days=3))
        key = f"booking-created-{response.data['id']}"
        self.assertIn(key, dedupe_keys(self.owner))

        listing = self.get("/api/notifications/", headers=self.owner_auth)
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.data["unread_count"], 1)
        self.assertEqual(listing.data["results"][0]["link"], f"/bookings/{response.data['id']}")

    def test_failed_booking_leaves_no_notification(self):
        poor = make_user("09140000000")
        self.book(self.now + timedelta(days=3), headers=auth_header(poor))
        self.assertEqual(Notification.objects.filter(user=self.owner).count(), 0)

    def test_cancellation_notifies_the_other_side(self):
        booking_id = self.book(self.now + timedelta(days=3)).data["id"]
        self.cancel(booking_id)
        self.assertIn(f"booking-cancelled-{booking_id}", dedupe_keys(self.owner))

        other_id = self.book(self.now + timedelta(days=6)).data["id"]
        self.cancel(other_id, headers=self.owner_auth)
        self.assertIn(f"booking-cancelled-{other_id}", dedupe_keys(self.renter))

    def test_finished_trip_notifies_both_sides(self):
        booking = self.finish_trip()
        self.assertIn(f"trip-ended-owner-{booking.pk}", dedupe_keys(self.owner))
        self.assertIn(f"trip-ended-renter-{booking.pk}", dedupe_keys(self.renter))

    def test_mark_read(self):
        self.book(self.now + timedelta(days=3))
        first = self.get("/api/notifications/", headers=self.owner_auth).data["results"][0]

        response = self.client.post(
            "/api/notifications/read/",
            {"ids": [first["id"]]},
            format="json",
            **self.owner_auth,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["updated"], 1)
        self.assertEqual(response.data["unread_count"], 0)

    def test_users_cannot_read_each_others_notifications(self):
        self.book(self.now + timedelta(days=3))
        owner_item = Notification.objects.get(user=self.owner)

        response = self.client.post(
            "/api/notifications/read/",
            {"ids": [owner_item.pk]},
            format="json",
            **self.auth,
        )
        self.assertEqual(response.data["updated"], 0)
        owner_item.refresh_from_db()
        self.assertIsNone(owner_item.read_at)

    def test_mark_all_read(self):
        self.book(self.now + timedelta(days=3))
        self.book(self.now + timedelta(days=6))
        response = self.client.post(
            "/api/notifications/read/", {"all": True}, format="json", **self.owner_auth
        )
        self.assertEqual(response.data["updated"], 2)
        self.assertEqual(response.data["unread_count"], 0)

    def test_unread_filter_and_count_endpoint(self):
        self.book(self.now + timedelta(days=3))
        count = self.get("/api/notifications/unread-count/", headers=self.owner_auth)
        self.assertEqual(count.data["count"], 1)
        unread = self.get("/api/notifications/?unread=1", headers=self.owner_auth)
        self.assertEqual(len(unread.data["results"]), 1)


class ReminderTests(TripTestCase):
    def count(self, headers=None):
        response = self.client.get(
            "/api/notifications/unread-count/",
            **(self.auth if headers is None else headers),
        )
        self.assertEqual(response.status_code, 200)
        return response.data["count"]

    def set_end(self, booking, end_at):
        Booking.objects.filter(pk=booking.pk).update(
            end_at=end_at, blocked_until=end_at + timedelta(minutes=30)
        )

    def test_start_reminder_is_created_once(self):
        self.raw_booking(self.now + timedelta(minutes=40))
        self.assertEqual(self.count(), 1)
        self.assertEqual(self.count(), 1)

    def test_far_future_booking_has_no_reminder(self):
        self.raw_booking(self.now + timedelta(days=2))
        self.assertEqual(self.count(), 0)

    def test_end_reminders_follow_the_remaining_time(self):
        booking = self.active_booking(start_offset_hours=-2, hours=3)

        self.set_end(booking, self.now + timedelta(minutes=10))
        self.assertEqual(self.count(), 1)
        self.assertEqual(self.count(), 1)

        self.set_end(booking, self.now + timedelta(minutes=3))
        self.assertEqual(self.count(), 2)

        self.set_end(booking, self.now - timedelta(minutes=5))
        self.assertEqual(self.count(), 3)
        reminder = Notification.objects.filter(
            user=self.renter, dedupe_key__startswith="overdue-"
        )
        self.assertEqual(reminder.count(), 1)

    def test_reminders_belong_to_the_renter_only(self):
        booking = self.active_booking(start_offset_hours=-2, hours=3)
        self.set_end(booking, self.now + timedelta(minutes=10))
        self.assertEqual(self.count(headers=self.owner_auth), 1)  # booking-created only
        self.assertEqual(
            Notification.objects.filter(
                user=self.owner, kind=Notification.Kind.REMINDER
            ).count(),
            0,
        )


class DecisionNotificationTests(TripTestCase):
    def test_identity_decisions_notify_the_user(self):
        user = make_user("09180000000", verified=False)

        user.verification_status = User.VerificationStatus.APPROVED
        user.save()
        self.assertEqual(
            Notification.objects.filter(user=user, kind="verification").count(), 1
        )

        user.verification_status = User.VerificationStatus.REJECTED
        user.rejection_reason = "Blurry photo"
        user.save()
        rejected = Notification.objects.filter(user=user, kind="verification").first()
        self.assertIn("Blurry photo", rejected.body)

    def test_saving_other_fields_does_not_notify(self):
        user = make_user("09180000001", verified=False)
        user.save(update_fields=["last_login"])
        user.first_name = "Sara"
        user.save()
        self.assertEqual(Notification.objects.filter(user=user).count(), 0)

    def test_vehicle_approval_notifies_the_owner(self):
        vehicle = make_vehicle(self.owner, approval_status="pending")
        vehicle.approval_status = Vehicle.ApprovalStatus.APPROVED
        vehicle.save()
        self.assertEqual(
            Notification.objects.filter(user=self.owner, kind="vehicle").count(), 1
        )

    def test_damage_report_notifies_the_renter(self):
        booking = self.finish_trip()
        response = self.client.post(
            f"/api/bookings/{booking.pk}/damage/",
            {"description": "Scratch", "claimed_amount": 500_000},
            format="json",
            **self.owner_auth,
        )
        self.assertEqual(response.status_code, 201)
        keys = dedupe_keys(self.renter)
        self.assertTrue(any(key.startswith("damage-created-") for key in keys))
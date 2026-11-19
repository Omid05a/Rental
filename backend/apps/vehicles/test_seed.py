import tempfile
from datetime import timedelta
from io import StringIO

from django.core.files.storage import FileSystemStorage
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.bookings.earnings import compute_earnings
from apps.bookings.models import Booking, DamageReport, InspectionPhoto
from apps.payments.models import Wallet
from apps.reviews.models import Review
from apps.users.models import User, VerificationDocument
from apps.vehicles.management.commands.seed_demo import AMIR, MEHDI, SARA
from apps.vehicles.models import Vehicle


def seed(*flags):
    out = StringIO()
    call_command("seed_demo", "--small", *flags, stdout=out)
    return out.getvalue()


class SeedDemoTests(TestCase):
    @classmethod
    def setUpClass(cls):
        # Keep the generated images in a temporary folder.
        cls._tmp = tempfile.TemporaryDirectory()
        cls._override = override_settings(MEDIA_ROOT=cls._tmp.name)
        cls._override.enable()
        cls._field = VerificationDocument._meta.get_field("file")
        cls._storage = cls._field.storage
        cls._field.storage = FileSystemStorage(location=f"{cls._tmp.name}/private")
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._field.storage = cls._storage
        cls._override.disable()
        cls._tmp.cleanup()

    @classmethod
    def setUpTestData(cls):
        seed()

    def owners(self):
        return Vehicle.objects.filter(owner__phone__in=[SARA[0], AMIR[0]])

    def test_vehicles_have_photos_and_one_is_pending(self):
        approved = self.owners().filter(approval_status="approved")
        self.assertEqual(approved.count(), 8)
        self.assertEqual(self.owners().filter(approval_status="pending").count(), 1)
        for vehicle in self.owners():
            self.assertEqual(vehicle.photos.count(), 3, vehicle.title)

    def test_trips_reviews_and_damage_claim(self):
        self.assertEqual(Booking.objects.filter(status="completed").count(), 4)
        self.assertEqual(Booking.objects.filter(status="confirmed").count(), 1)
        self.assertEqual(Review.objects.count(), 5)

        report = DamageReport.objects.get()
        self.assertEqual(report.status, "open")
        self.assertEqual(
            report.booking.photos.filter(phase=InspectionPhoto.Phase.DAMAGE).count(), 2
        )
        self.assertEqual(
            InspectionPhoto.objects.filter(phase__in=["start", "end"]).count(), 24
        )

    def test_pending_user_has_all_documents(self):
        user = User.objects.get(phone=MEHDI[0])
        self.assertEqual(user.verification_status, "pending")
        self.assertEqual(user.documents.count(), 4)

    def test_every_wallet_matches_its_ledger(self):
        for wallet in Wallet.objects.all():
            total = sum(item.amount for item in wallet.transactions.all())
            self.assertEqual(total, wallet.balance, wallet.user.phone)
            self.assertGreaterEqual(wallet.balance, 0)

    def test_earnings_add_up(self):
        sara = User.objects.get(phone=SARA[0])
        amir = User.objects.get(phone=AMIR[0])
        self.assertEqual(compute_earnings(sara)["total_net"], 2_103_750)
        self.assertEqual(compute_earnings(amir)["total_net"], 2_601_000)

    def test_running_again_keeps_the_existing_data(self):
        output = seed()
        self.assertIn("already exists", output)
        self.assertEqual(self.owners().count(), 9)

    def test_reset_recreates_the_same_data(self):
        seed("--reset")
        self.assertEqual(self.owners().count(), 9)
        self.assertEqual(Booking.objects.filter(status="completed").count(), 4)
        self.assertEqual(Review.objects.count(), 5)

    def test_live_booking_starts_soon_and_is_replaced_on_rerun(self):
        soon = timezone.now() + timedelta(minutes=15)
        seed("--live")
        live = Booking.objects.filter(status="confirmed", start_at__lte=soon)
        self.assertEqual(live.count(), 1)

        seed("--live")
        self.assertEqual(
            Booking.objects.filter(status="confirmed", start_at__lte=soon).count(), 1
        )

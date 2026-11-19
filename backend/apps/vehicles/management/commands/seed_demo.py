from datetime import timedelta

from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.bookings.models import Booking, DamageReport, InspectionPhoto
from apps.bookings.pricing import (
    billable_late_minutes,
    fuel_fee_amount,
    late_fee_amount,
    platform_share,
    rental_amount,
)
from apps.bookings.services import BookingError, cancel_booking, create_booking
from apps.bookings.terms import TERMS_VERSION
from apps.bookings.trips import required_angles
from apps.payments.models import WalletTransaction
from apps.payments.services import apply_transaction, get_or_create_wallet
from apps.reviews.models import Review
from apps.users.models import User, VerificationDocument
from apps.vehicles import demo_images
from apps.vehicles.models import Vehicle, VehiclePhoto

Kind = WalletTransaction.Kind

# (phone, first name, last name). All names are fictional.
SARA = ("09100000001", "سارا", "احمدی")  # owner
REZA = ("09100000002", "رضا", "کریمی")  # renter
AMIR = ("09100000003", "امیر", "حسینی")  # owner
NEDA = ("09100000004", "ندا", "رحیمی")  # renter
MEHDI = ("09100000005", "مهدی", "صالحی")  # new user waiting for review
ALL_PHONES = [person[0] for person in (SARA, REZA, AMIR, NEDA, MEHDI)]

LIVE_VEHICLE = "دوچرخه کوهستان"

VEHICLES = [
    {
        "owner": "sara", "kind": "car", "title": "پژو ۲۰۶ تیپ ۵", "brand": "پژو",
        "model": "۲۰۶", "year": 1395, "gear": "manual", "fuel": "gasoline", "seats": 5,
        "hourly": 90_000, "daily": 700_000, "deposit": 10_000_000, "km": 250,
        "lat": 35.7020, "lng": 51.4090, "address": "میدان ولیعصر، تهران",
        "color": "#B3392F",
        "description": "تمیز و اقتصادی، مناسب رفت‌وآمد شهری. پارک در پارکینگ اختصاصی.",
    },
    {
        "owner": "amir", "kind": "car", "title": "سمند LX", "brand": "ایران‌خودرو",
        "model": "سمند", "year": 1394, "gear": "manual", "fuel": "gasoline", "seats": 5,
        "hourly": 80_000, "daily": 600_000, "deposit": 8_000_000, "km": 250,
        "lat": 35.7010, "lng": 51.3910, "address": "میدان انقلاب، تهران",
        "color": "#E8E4DA",
        "description": "فضای داخلی بزرگ و صندوق عقب جادار، مناسب سفرهای خانوادگی.",
    },
    {
        "owner": "sara", "kind": "car", "title": "کیا سراتو", "brand": "کیا",
        "model": "سراتو", "year": 1398, "gear": "automatic", "fuel": "gasoline", "seats": 5,
        "hourly": 200_000, "daily": 1_500_000, "deposit": 30_000_000, "km": 300,
        "lat": 35.7570, "lng": 51.4090, "address": "میدان ونک، تهران",
        "color": "#2F5D9E",
        "description": "اتوماتیک و راحت، با سیستم صوتی خوب. سیگار ممنوع.",
    },
    {
        "owner": "amir", "kind": "car", "title": "هیوندای النترا", "brand": "هیوندای",
        "model": "النترا", "year": 1397, "gear": "automatic", "fuel": "gasoline", "seats": 5,
        "hourly": 220_000, "daily": 1_700_000, "deposit": 35_000_000, "km": 300,
        "lat": 35.8040, "lng": 51.4330, "address": "تجریش، تهران",
        "color": "#9AA3AD",
        "description": "سدان راحت با صندلی گرم‌شونده، مناسب مسیرهای طولانی.",
    },
    {
        "owner": "amir", "kind": "car", "title": "تویوتا یاریس", "brand": "تویوتا",
        "model": "یاریس", "year": 1396, "gear": "automatic", "fuel": "gasoline", "seats": 5,
        "hourly": 180_000, "daily": 1_300_000, "deposit": 25_000_000, "km": 250,
        "lat": 35.6997, "lng": 51.3380, "address": "میدان آزادی، تهران",
        "color": "#D9822B",
        "description": "کم‌مصرف و چابک، مناسب ترافیک شهری و پارک آسان.",
    },
    {
        "owner": "sara", "kind": "bike", "title": "دوچرخه شهری", "brand": "جاینت",
        "model": "Escape", "hourly": 25_000, "daily": 150_000, "deposit": 2_000_000,
        "lat": 35.7150, "lng": 51.2700, "address": "صادقیه، تهران",
        "color": "#2E8B7A",
        "description": "زین راحت و سبد جلو. قفل و کلاه ایمنی همراه دوچرخه است.",
    },
    {
        "owner": "sara", "kind": "bike", "title": LIVE_VEHICLE, "brand": "مریدا",
        "model": "Big Nine", "hourly": 30_000, "daily": 200_000, "deposit": 3_000_000,
        "lat": 35.7360, "lng": 51.5130, "address": "تهرانپارس، تهران",
        "color": "#D9822B",
        "description": "مناسب مسیرهای ناهموار و پارک. ۲۱ دنده و ترمز دیسکی.",
    },
    {
        "owner": "amir", "kind": "bike", "title": "دوچرخه برقی", "brand": "شیائومی",
        "model": "Himo", "hourly": 45_000, "daily": 300_000, "deposit": 5_000_000,
        "lat": 35.7570, "lng": 51.3640, "address": "شهرک غرب، تهران",
        "color": "#3A3F46",
        "description": "برد حدود ۴۰ کیلومتر با یک شارژ. شارژر همراه آن است.",
    },
    {
        "owner": "amir", "kind": "car", "title": "پراید ۱۳۱ SE", "brand": "سایپا",
        "model": "پراید", "year": 1393, "gear": "manual", "fuel": "gasoline", "seats": 4,
        "hourly": 70_000, "daily": 520_000, "deposit": 6_000_000, "km": 200,
        "lat": 35.6892, "lng": 51.3890, "address": "میدان امام خمینی، تهران",
        "color": "#E8E4DA", "status": Vehicle.ApprovalStatus.PENDING,
        "description": "این وسیله در صف بررسی ادمین است.",
    },
]

PHOTO_VARIANTS = [
    {"theme": "dusk", "zoom": 1.0, "focus": 0.5},
    {"theme": "day", "zoom": 1.0, "focus": 0.5, "mirror": True},
    {"theme": "dawn", "zoom": 1.55, "focus": 0.85},
]


class Command(BaseCommand):
    help = (
        "Creates a complete demo: owners, renters, vehicles with generated "
        "illustrations, finished trips with inspection photos, reviews, an open "
        "damage claim, a pending user and vehicle for the admin, and a funded wallet."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete the demo accounts and everything they own, then recreate.",
        )
        parser.add_argument(
            "--live",
            action="store_true",
            help="Create a booking for the demo renter that starts in 10 minutes.",
        )
        parser.add_argument(
            "--small",
            action="store_true",
            help="Use smaller, faster images (used by the tests).",
        )

    # ------------------------------------------------------------ entry

    def handle(self, *args, **options):
        self.small = options["small"]
        self.colors = {}

        if options["reset"]:
            with transaction.atomic():
                self.wipe()
                self.seed()
        elif Vehicle.objects.filter(owner__phone__in=[SARA[0], AMIR[0]]).exists():
            self.stdout.write("Demo data already exists. Use --reset to recreate it.")
        else:
            with transaction.atomic():
                self.seed()

        if options["live"]:
            self.create_live_booking()

        self.print_summary()

    # ------------------------------------------------------------ sizes

    def vehicle_size(self):
        return (600, 400) if self.small else (1200, 800)

    def inspection_size(self):
        return (450, 300) if self.small else (900, 600)

    # ------------------------------------------------------------- wipe

    def wipe(self):
        bookings = Booking.objects.filter(
            Q(renter__phone__in=ALL_PHONES) | Q(vehicle__owner__phone__in=ALL_PHONES)
        )
        for photo in InspectionPhoto.objects.filter(booking__in=bookings):
            photo.image.delete(save=False)
        bookings.delete()

        for photo in VehiclePhoto.objects.filter(vehicle__owner__phone__in=ALL_PHONES):
            photo.image.delete(save=False)
        Vehicle.objects.filter(owner__phone__in=ALL_PHONES).delete()

        for document in VerificationDocument.objects.filter(user__phone__in=ALL_PHONES):
            document.file.delete(save=False)
        User.objects.filter(phone__in=ALL_PHONES).delete()

    # ------------------------------------------------------------- seed

    def seed(self):
        owners = {
            "sara": self.make_user(SARA),
            "amir": self.make_user(AMIR),
        }
        reza = self.make_user(REZA)
        neda = self.make_user(NEDA)
        self.ensure_funds(reza, 20_000_000)
        self.ensure_funds(neda, 20_000_000)

        vehicles = {}
        for index, spec in enumerate(VEHICLES):
            vehicle = self.create_vehicle(spec, owners[spec["owner"]], index)
            vehicles[spec["title"]] = vehicle

        self.create_history(reza, neda, vehicles)
        self.create_newcomer()

    def make_user(self, person, status=User.VerificationStatus.APPROVED):
        phone, first_name, last_name = person
        user = User.objects.filter(phone=phone).first()
        if user is None:
            return User.objects.create_user(
                phone=phone,
                first_name=first_name,
                last_name=last_name,
                verification_status=status,
            )
        user.first_name = first_name
        user.last_name = last_name
        user.verification_status = status
        user.rejection_reason = ""
        user.save(
            update_fields=[
                "first_name",
                "last_name",
                "verification_status",
                "rejection_reason",
            ]
        )
        return user

    def ensure_funds(self, user, needed):
        balance = get_or_create_wallet(user).balance
        if balance < needed:
            apply_transaction(
                user, needed - balance + 5_000_000, Kind.TOPUP, reference="seed"
            )

    def create_vehicle(self, spec, owner, index):
        is_car = spec["kind"] == "car"
        fields = {
            "owner": owner,
            "kind": spec["kind"],
            "title": spec["title"],
            "brand": spec["brand"],
            "model_name": spec["model"],
            "year": spec.get("year"),
            "description": spec["description"],
            "price_per_hour": spec["hourly"],
            "price_per_day": spec["daily"],
            "deposit": spec["deposit"],
            "location": Point(spec["lng"], spec["lat"], srid=4326),
            "address": spec["address"],
            "approval_status": spec.get("status", Vehicle.ApprovalStatus.APPROVED),
        }
        if is_car:
            fields.update(
                transmission=spec["gear"],
                fuel_type=spec["fuel"],
                seats=spec["seats"],
                insurance_expiry=timezone.localdate() + timedelta(days=200),
                daily_km_limit=spec["km"],
                min_fuel_percent=25,
            )
        else:
            fields.update(min_fuel_percent=None, pickup_radius_m=30)

        vehicle = Vehicle.objects.create(**fields)
        self.colors[vehicle.pk] = spec["color"]

        for position, variant in enumerate(PHOTO_VARIANTS):
            data = demo_images.render_vehicle(
                vehicle.kind,
                spec["color"],
                seed=index * 10 + position,
                size=self.vehicle_size(),
                **variant,
            )
            photo = VehiclePhoto(vehicle=vehicle, position=position)
            photo.image.save(f"demo-{vehicle.pk}-{position}.jpg", ContentFile(data))
        return vehicle

    def create_newcomer(self):
        user = self.make_user(MEHDI, User.VerificationStatus.PENDING)
        for doc_type in VerificationDocument.DocType.values:
            data = demo_images.render_document(doc_type, size=self.inspection_size())
            document = VerificationDocument(user=user, doc_type=doc_type)
            document.file.save(f"{doc_type}.jpg", ContentFile(data))

    # ---------------------------------------------------------- history

    def create_history(self, reza, neda, vehicles):
        sara_car = vehicles["کیا سراتو"]
        amir_car = vehicles["هیوندای النترا"]
        city_bike = vehicles["دوچرخه شهری"]
        peugeot = vehicles["پژو ۲۰۶ تیپ ۵"]
        yaris = vehicles["تویوتا یاریس"]

        # 1. A clean trip, reviewed by both sides.
        first = self.completed_booking(
            renter=reza, vehicle=sara_car, days_ago=6, hour=10, hours=5,
            start_fuel=80, end_fuel=78, photos=True,
        )
        self.review(first, reza, 5, "ماشین تمیز و تحویل بدون دردسر بود.")
        self.review(first, sara_car.owner, 5, "اجاره‌کننده منظم و به‌موقع بود.")

        # 2. A late return with low fuel and an open damage claim (for the admin).
        second = self.completed_booking(
            renter=neda, vehicle=amir_car, days_ago=2, hour=9, hours=24,
            late_after_end=95, start_fuel=90, end_fuel=60, hold_deposit=True,
            photos=True, scratch_end=True,
        )
        self.damage_claim(second, amir_car)

        # 3. A recent bike trip where only the renter has written a review so far.
        third = self.completed_booking(
            renter=reza, vehicle=city_bike, days_ago=4, hour=15, hours=3, photos=True
        )
        self.review(third, reza, 5, "دوچرخه سالم و زین راحتی داشت.")

        # 4. An older trip that fills the previous month of the earnings chart.
        fourth = self.completed_booking(
            renter=neda, vehicle=peugeot, days_ago=35, hour=11, hours=48,
            start_fuel=70, end_fuel=68,
        )
        self.review(fourth, neda, 4, "ماشین اقتصادی و مناسب بود.")
        self.review(fourth, peugeot.owner, 5, "مستاجر محترم و دقیق.")

        # 5. An upcoming booking created through the real booking service.
        start = timezone.localtime(timezone.now() + timedelta(days=2)).replace(
            hour=9, minute=0, second=0, microsecond=0
        )
        create_booking(
            renter=reza,
            vehicle_id=yaris.pk,
            start_at=start,
            end_at=start + timedelta(hours=8),
            terms_version=TERMS_VERSION,
        )

    def completed_booking(
        self, *, renter, vehicle, days_ago, hour, hours, late_after_end=0,
        start_fuel=None, end_fuel=None, hold_deposit=False, photos=False,
        scratch_end=False,
    ):
        now = timezone.now()
        start = timezone.localtime(now - timedelta(days=days_ago)).replace(
            hour=hour, minute=0, second=0, microsecond=0
        )
        end = start + timedelta(hours=hours)
        ended_at = end + timedelta(minutes=late_after_end)

        rental = rental_amount(hours, vehicle.price_per_hour, vehicle.price_per_day)
        deposit = vehicle.deposit
        late_minutes = billable_late_minutes(end, ended_at)
        late_fee = min(late_fee_amount(late_minutes, vehicle.price_per_hour), deposit)
        fuel_fee = min(fuel_fee_amount(start_fuel, end_fuel), deposit - late_fee)
        owner_gross = rental + late_fee + fuel_fee
        platform_fee = platform_share(owner_gross)

        self.ensure_funds(renter, rental + deposit)
        booking = Booking.objects.create(
            renter=renter,
            vehicle=vehicle,
            status=Booking.Status.COMPLETED,
            start_at=start,
            end_at=end,
            blocked_until=end + timedelta(minutes=30),
            hours=hours,
            price_per_hour=vehicle.price_per_hour,
            price_per_day=vehicle.price_per_day,
            rental_amount=rental,
            deposit_amount=deposit,
            total_paid=rental + deposit,
            terms_version=TERMS_VERSION,
            terms_accepted_at=start - timedelta(days=1),
            started_at=start,
            ended_at=ended_at,
            start_fuel_percent=start_fuel,
            end_fuel_percent=end_fuel,
            late_minutes=late_minutes,
            late_fee=late_fee,
            fuel_fee=fuel_fee,
            platform_fee=platform_fee,
            deposit_status=(
                Booking.DepositStatus.HELD
                if hold_deposit
                else Booking.DepositStatus.RELEASED
            ),
            deposit_release_at=(
                now + timedelta(hours=20)
                if hold_deposit
                else ended_at + timedelta(hours=settings.DAMAGE_WINDOW_HOURS)
            ),
            created_at=start - timedelta(days=2),
        )

        reference = f"booking:{booking.pk}"
        apply_transaction(renter, -rental, Kind.BOOKING_CHARGE, reference=reference)
        apply_transaction(renter, -deposit, Kind.DEPOSIT_HOLD, reference=reference)
        apply_transaction(
            vehicle.owner, owner_gross - platform_fee, Kind.PAYOUT, reference=reference
        )
        if not hold_deposit and deposit - late_fee - fuel_fee > 0:
            apply_transaction(
                renter, deposit - late_fee - fuel_fee, Kind.REFUND, reference=reference
            )

        if photos:
            self.inspection_photos(booking, vehicle, scratch_end)
        return booking

    def inspection_photos(self, booking, vehicle, scratch_end):
        color = self.colors[vehicle.pk]
        steps = (
            ("start", booking.start_fuel_percent, booking.started_at),
            ("end", booking.end_fuel_percent, booking.ended_at),
        )
        for phase, fuel, taken_at in steps:
            for angle in required_angles(vehicle.kind):
                data = demo_images.render_inspection(
                    vehicle.kind,
                    color,
                    angle,
                    phase,
                    seed=booking.pk,
                    fuel=fuel,
                    scratch=scratch_end and phase == "end",
                    size=self.inspection_size(),
                )
                photo = InspectionPhoto(
                    booking=booking,
                    phase=phase,
                    angle=angle,
                    latitude=vehicle.latitude,
                    longitude=vehicle.longitude,
                    taken_at=taken_at,
                )
                photo.image.save(f"{phase}-{angle}.jpg", ContentFile(data))

    def review(self, booking, author, rating, comment):
        renter_writes = author.pk == booking.renter_id
        Review.objects.create(
            booking=booking,
            author=author,
            subject=booking.vehicle.owner if renter_writes else booking.renter,
            direction=(
                Review.Direction.RENTER_TO_OWNER
                if renter_writes
                else Review.Direction.OWNER_TO_RENTER
            ),
            rating=rating,
            comment=comment,
            created_at=booking.ended_at + timedelta(hours=3),
        )

    def damage_claim(self, booking, vehicle):
        DamageReport.objects.create(
            booking=booking,
            description="خط و خش روی درب سمت راست که قبل از سفر وجود نداشت.",
            claimed_amount=1_500_000,
        )
        color = self.colors[vehicle.pk]
        for index in range(2):
            data = demo_images.render_vehicle(
                vehicle.kind,
                color,
                theme="day",
                zoom=1.4,
                focus=0.5,
                seed=40 + index,
                size=self.inspection_size(),
                scratch=True,
                mirror=True,
                label="DAMAGE REPORT",
            )
            photo = InspectionPhoto(
                booking=booking,
                phase=InspectionPhoto.Phase.DAMAGE,
                angle=InspectionPhoto.Angle.DAMAGE,
                latitude=vehicle.latitude,
                longitude=vehicle.longitude,
            )
            photo.image.save(f"damage-{index}.jpg", ContentFile(data))

    # ------------------------------------------------------------- live

    def create_live_booking(self):
        renter = User.objects.filter(phone=REZA[0]).first()
        vehicle = Vehicle.objects.filter(
            owner__phone=SARA[0], title=LIVE_VEHICLE
        ).first()
        if renter is None or vehicle is None:
            raise CommandError("Demo data is missing. Run seed_demo first.")

        # Remove an earlier live booking so the new one does not overlap with it.
        stale = Booking.objects.filter(
            renter=renter, vehicle=vehicle, status=Booking.Status.CONFIRMED
        )
        for booking in stale:
            try:
                cancel_booking(booking_id=booking.pk, user=renter, reason="demo reset")
            except BookingError:
                Booking.objects.filter(pk=booking.pk).update(
                    status=Booking.Status.CANCELLED
                )

        self.ensure_funds(renter, 2_000_000)
        start = timezone.now() + timedelta(minutes=10)
        booking, _ = create_booking(
            renter=renter,
            vehicle_id=vehicle.pk,
            start_at=start,
            end_at=start + timedelta(hours=2),
            terms_version=TERMS_VERSION,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Live booking #{booking.pk} starts in about 10 minutes "
                f"({vehicle.title}, renter {REZA[0]})."
            )
        )

    # ---------------------------------------------------------- summary

    def print_summary(self):
        self.stdout.write(self.style.SUCCESS("Demo data is ready. Log in with an OTP code:"))
        for person, role in (
            (SARA, "owner of 3 cars/bikes with reviews and earnings"),
            (AMIR, "owner with an open damage claim to settle in the admin"),
            (REZA, "renter with trips, an upcoming booking and 20M Toman"),
            (NEDA, "renter whose trip has fees and a damage claim"),
            (MEHDI, "new user waiting for identity review in the admin"),
        ):
            self.stdout.write(f"  {person[0]}  {person[1]} {person[2]}: {role}")
        self.stdout.write(
            "In the admin: approve the pending vehicle, review the new user's "
            "documents, and settle the damage claim."
        )

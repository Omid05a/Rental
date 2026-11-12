from datetime import timedelta

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.users.models import User
from apps.vehicles.models import Vehicle

DEMO_PHONE = "09100000001"

CARS = [
    # title, brand, model, year (Solar Hijri), transmission, hourly, daily, deposit, lat, lng, address
    ("پژو ۲۰۶ تیپ ۵", "پژو", "۲۰۶", 1395, "manual", 90_000, 700_000, 10_000_000, 35.7020, 51.4090, "میدان ولیعصر، تهران"),
    ("سمند LX", "ایران‌خودرو", "سمند", 1394, "manual", 80_000, 600_000, 8_000_000, 35.7010, 51.3910, "میدان انقلاب، تهران"),
    ("کیا سراتو", "کیا", "سراتو", 1398, "automatic", 200_000, 1_500_000, 30_000_000, 35.7570, 51.4090, "میدان ونک، تهران"),
    ("هیوندای النترا", "هیوندای", "النترا", 1397, "automatic", 220_000, 1_700_000, 35_000_000, 35.8040, 51.4330, "تجریش، تهران"),
    ("تویوتا یاریس", "تویوتا", "یاریس", 1396, "automatic", 180_000, 1_300_000, 25_000_000, 35.6997, 51.3380, "میدان آزادی، تهران"),
]

BIKES = [
    # title, brand, model, hourly, daily, deposit, lat, lng, address
    ("دوچرخه شهری", "جاینت", "Escape", 25_000, 150_000, 2_000_000, 35.7150, 51.2700, "صادقیه، تهران"),
    ("دوچرخه کوهستان", "مریدا", "Big Nine", 30_000, 200_000, 3_000_000, 35.7360, 51.5130, "تهرانپارس، تهران"),
    ("دوچرخه برقی", "شیائومی", "Himo", 45_000, 300_000, 5_000_000, 35.7570, 51.3640, "شهرک غرب، تهران"),
]


class Command(BaseCommand):
    help = "Creates a demo owner (09100000001) and sample vehicles around Tehran."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete the demo owner's vehicles before creating new ones.",
        )

    def handle(self, *args, **options):
        owner = User.objects.filter(phone=DEMO_PHONE).first()
        if owner is None:
            owner = User.objects.create_user(
                phone=DEMO_PHONE,
                first_name="سارا",
                last_name="احمدی",
                verification_status=User.VerificationStatus.APPROVED,
            )

        if options["reset"]:
            owner.vehicles.all().delete()
        elif owner.vehicles.exists():
            self.stdout.write("Demo vehicles already exist. Use --reset to recreate.")
            return

        insurance = timezone.localdate() + timedelta(days=200)
        approved = Vehicle.ApprovalStatus.APPROVED

        for title, brand, model, year, gear, hourly, daily, deposit, lat, lng, address in CARS:
            Vehicle.objects.create(
                owner=owner,
                kind=Vehicle.Kind.CAR,
                title=title,
                brand=brand,
                model_name=model,
                year=year,
                transmission=gear,
                fuel_type=Vehicle.FuelType.GASOLINE,
                seats=5,
                insurance_expiry=insurance,
                price_per_hour=hourly,
                price_per_day=daily,
                deposit=deposit,
                daily_km_limit=250,
                location=Point(lng, lat, srid=4326),
                address=address,
                approval_status=approved,
            )

        for title, brand, model, hourly, daily, deposit, lat, lng, address in BIKES:
            Vehicle.objects.create(
                owner=owner,
                kind=Vehicle.Kind.BIKE,
                title=title,
                brand=brand,
                model_name=model,
                price_per_hour=hourly,
                price_per_day=daily,
                deposit=deposit,
                min_fuel_percent=None,
                pickup_radius_m=30,
                location=Point(lng, lat, srid=4326),
                address=address,
                approval_status=approved,
            )

        self.stdout.write(
            self.style.SUCCESS(f"Created {len(CARS) + len(BIKES)} demo vehicles.")
        )
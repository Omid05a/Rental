from datetime import timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from .pricing import billable_hours, cancellation_fee, platform_share, rental_amount

HOURLY = 100_000
DAILY = 900_000


class PricingTests(SimpleTestCase):
    def test_short_rental_uses_hourly_price(self):
        self.assertEqual(rental_amount(5, HOURLY, DAILY), 500_000)

    def test_many_hours_are_capped_by_daily_price(self):
        self.assertEqual(rental_amount(20, HOURLY, DAILY), DAILY)

    def test_day_plus_one_hour(self):
        self.assertEqual(rental_amount(25, HOURLY, DAILY), DAILY + HOURLY)

    def test_two_days(self):
        self.assertEqual(rental_amount(48, HOURLY, DAILY), 2 * DAILY)

    def test_partial_hours_round_up(self):
        start = timezone.now()
        self.assertEqual(billable_hours(start, start + timedelta(minutes=60)), 1)
        self.assertEqual(billable_hours(start, start + timedelta(minutes=61)), 2)

    def test_cancellation_is_free_far_before_start(self):
        now = timezone.now()
        fee = cancellation_fee(
            rental_amount=500_000,
            price_per_day=DAILY,
            start_at=now + timedelta(days=2),
            now=now,
        )
        self.assertEqual(fee, 0)

    def test_late_cancellation_fee_is_half_of_first_day(self):
        now = timezone.now()
        soon = now + timedelta(hours=5)
        short = cancellation_fee(
            rental_amount=500_000, price_per_day=DAILY, start_at=soon, now=now
        )
        long_rental = cancellation_fee(
            rental_amount=2_000_000, price_per_day=DAILY, start_at=soon, now=now
        )
        self.assertEqual(short, 250_000)
        self.assertEqual(long_rental, 450_000)

    def test_platform_share(self):
        self.assertEqual(platform_share(250_000), 37_500)
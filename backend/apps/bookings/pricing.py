from datetime import timedelta

from django.conf import settings


def billable_hours(start_at, end_at):
    """Duration in whole hours, rounded up (61 minutes are billed as 2 hours)."""
    seconds = int((end_at - start_at).total_seconds())
    return max(1, -(-seconds // 3600))


def rental_amount(hours, price_per_hour, price_per_day):
    """Full days cost the daily price; the remaining hours cost the cheaper of
    the hourly total and one daily price."""
    days, remainder = divmod(hours, 24)
    amount = days * price_per_day
    if remainder:
        amount += min(remainder * price_per_hour, price_per_day)
    return amount


def cancellation_fee(*, rental_amount, price_per_day, start_at, now):
    """Free far before the start; later, a share of the first day's cost."""
    if start_at - now > timedelta(hours=settings.CANCEL_FREE_HOURS):
        return 0
    first_day = min(rental_amount, price_per_day)
    return first_day * settings.CANCEL_LATE_FEE_PERCENT // 100


def platform_share(amount):
    return amount * settings.COMMISSION_PERCENT // 100
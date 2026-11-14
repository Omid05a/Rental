from datetime import timedelta

from django.utils import timezone

from apps.notifications.models import Notification
from apps.notifications.services import fa, notify

from .models import Booking

Kind = Notification.Kind


def generate_due_reminders(user, now=None):
    """Creates time-based reminders for a user. Safe to call repeatedly: every
    reminder has a dedupe key, so it is created only once."""
    now = now or timezone.now()
    created = 0

    upcoming = Booking.objects.filter(
        renter=user,
        status=Booking.Status.CONFIRMED,
        start_at__gt=now,
        start_at__lte=now + timedelta(hours=1),
    ).select_related("vehicle")
    for booking in upcoming:
        minutes = max(1, int((booking.start_at - now).total_seconds() // 60))
        if notify(
            user,
            Kind.REMINDER,
            "سفر شما به‌زودی شروع می‌شود",
            f"رزرو «{booking.vehicle.title}» حدود {fa(minutes)} دقیقه دیگر شروع می‌شود. "
            "از ۱۵ دقیقه قبل از شروع می‌توانید عکس بگیرید و قفل را باز کنید.",
            f"/bookings/{booking.pk}",
            f"start-soon-{booking.pk}",
        ):
            created += 1

    active = Booking.objects.filter(
        renter=user, status=Booking.Status.ACTIVE
    ).select_related("vehicle")
    for booking in active:
        remaining = booking.end_at - now
        stamp = int(booking.end_at.timestamp())
        link = f"/bookings/{booking.pk}/trip"
        title = booking.vehicle.title

        if remaining <= timedelta(0):
            key = f"overdue-{booking.pk}-{stamp}"
            heading = "زمان اجاره تمام شده است"
            body = (
                f"زمان اجاره «{title}» تمام شده است. برای جلوگیری از جریمه تأخیر، "
                "وسیله را برگردانید یا اجاره را تمدید کنید."
            )
        elif remaining <= timedelta(minutes=5):
            key = f"end5-{booking.pk}-{stamp}"
            heading = "۵ دقیقه تا پایان اجاره"
            body = f"اجاره «{title}» کمتر از ۵ دقیقه دیگر تمام می‌شود."
        elif remaining <= timedelta(minutes=15):
            key = f"end15-{booking.pk}-{stamp}"
            heading = "۱۵ دقیقه تا پایان اجاره"
            body = (
                f"اجاره «{title}» کمتر از ۱۵ دقیقه دیگر تمام می‌شود. "
                "می‌توانید تمدید کنید یا وسیله را برگردانید."
            )
        else:
            continue

        if notify(user, Kind.REMINDER, heading, body, link, key):
            created += 1

    return created
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.notifications.models import Notification
from apps.notifications.services import notify, toman

from .models import Booking, DamageReport

Kind = Notification.Kind


def _name(user, fallback="یک کاربر"):
    return user.first_name or fallback


@receiver(pre_save, sender=Booking)
def remember_booking_state(sender, instance, **kwargs):
    instance._previous = (
        Booking.objects.filter(pk=instance.pk)
        .values("status", "deposit_status", "end_at")
        .first()
        if instance.pk
        else None
    )


@receiver(post_save, sender=Booking)
def booking_notifications(sender, instance, created, raw=False, **kwargs):
    if raw:
        return

    vehicle = instance.vehicle
    owner = vehicle.owner
    renter = instance.renter
    link = f"/bookings/{instance.pk}"

    if created:
        notify(
            owner,
            Kind.BOOKING,
            "رزرو جدید برای وسیله شما",
            f"«{vehicle.title}» توسط {_name(renter)} رزرو شد.",
            link,
            f"booking-created-{instance.pk}",
        )
        return

    previous = getattr(instance, "_previous", None)
    if not previous:
        return

    Status = Booking.Status

    if previous["status"] != instance.status:
        if instance.status == Status.CANCELLED:
            if instance.cancelled_by == "renter":
                notify(
                    owner,
                    Kind.BOOKING,
                    "رزرو لغو شد",
                    f"رزرو «{vehicle.title}» توسط اجاره‌کننده لغو شد.",
                    link,
                    f"booking-cancelled-{instance.pk}",
                )
            else:
                notify(
                    renter,
                    Kind.BOOKING,
                    "مالک رزرو را لغو کرد",
                    f"رزرو «{vehicle.title}» توسط مالک لغو شد و مبلغ کامل به کیف پول شما برگشت.",
                    link,
                    f"booking-cancelled-{instance.pk}",
                )

        elif instance.status == Status.ACTIVE:
            notify(
                owner,
                Kind.TRIP,
                "سفر شروع شد",
                f"{_name(renter)} سفر با «{vehicle.title}» را شروع کرد.",
                link,
                f"trip-started-{instance.pk}",
            )

        elif instance.status == Status.COMPLETED:
            net = (
                instance.rental_amount
                + instance.late_fee
                + instance.fuel_fee
                - instance.platform_fee
            )
            notify(
                owner,
                Kind.PAYMENT,
                "سفر پایان یافت",
                f"وسیله «{vehicle.title}» برگشت. درآمد خالص {toman(net)} به کیف پول شما واریز شد.",
                link,
                f"trip-ended-owner-{instance.pk}",
            )
            notify(
                renter,
                Kind.TRIP,
                "سفر شما پایان یافت",
                "سپرده تا پایان مهلت گزارش خسارت نگه داشته می‌شود و بعد از آن "
                "باقی‌مانده به کیف پول شما برمی‌گردد.",
                link,
                f"trip-ended-renter-{instance.pk}",
            )

    if (
        instance.status == Status.ACTIVE
        and previous["end_at"] != instance.end_at
    ):
        notify(
            owner,
            Kind.TRIP,
            "اجاره تمدید شد",
            f"اجاره «{vehicle.title}» تمدید شد.",
            link,
            f"trip-extended-{instance.pk}-{int(instance.end_at.timestamp())}",
        )

    if (
        instance.status == Status.COMPLETED
        and previous["deposit_status"] == Booking.DepositStatus.HELD
        and instance.deposit_status == Booking.DepositStatus.RELEASED
    ):
        left = instance.deposit_remaining
        body = (
            f"{toman(left)} از سپرده به کیف پول شما برگشت."
            if left > 0
            else "سپرده‌ای برای بازگشت باقی نماند."
        )
        notify(
            renter,
            Kind.PAYMENT,
            "سپرده شما تسویه شد",
            body,
            link,
            f"deposit-released-{instance.pk}",
        )


@receiver(pre_save, sender=DamageReport)
def remember_report_state(sender, instance, **kwargs):
    instance._previous = (
        DamageReport.objects.filter(pk=instance.pk)
        .values("status", "renter_response")
        .first()
        if instance.pk
        else None
    )


@receiver(post_save, sender=DamageReport)
def damage_notifications(sender, instance, created, raw=False, **kwargs):
    if raw:
        return

    booking = instance.booking
    owner = booking.vehicle.owner
    renter = booking.renter
    link = f"/bookings/{booking.pk}"

    if created:
        notify(
            renter,
            Kind.DAMAGE,
            "برای سفر شما گزارش خسارت ثبت شد",
            f"مالک مبلغ {toman(instance.claimed_amount)} را مطالبه کرده است. می‌توانید پاسخ دهید.",
            link,
            f"damage-created-{instance.pk}",
        )
        return

    previous = getattr(instance, "_previous", None)
    if not previous:
        return

    if instance.renter_response and previous["renter_response"] != instance.renter_response:
        notify(
            owner,
            Kind.DAMAGE,
            "اجاره‌کننده به گزارش خسارت پاسخ داد",
            "پاسخ اجاره‌کننده را در جزئیات رزرو ببینید.",
            link,
            f"damage-response-{instance.pk}",
        )

    if previous["status"] == DamageReport.Status.OPEN and (
        instance.status == DamageReport.Status.RESOLVED
    ):
        text = (
            f"گزارش خسارت بررسی شد. مبلغ تأییدشده: {toman(instance.approved_amount)}."
        )
        notify(owner, Kind.DAMAGE, "گزارش خسارت تسویه شد", text, link,
               f"damage-resolved-owner-{instance.pk}")
        notify(renter, Kind.DAMAGE, "گزارش خسارت تسویه شد", text, link,
               f"damage-resolved-renter-{instance.pk}")
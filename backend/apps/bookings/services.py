from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.payments.models import WalletTransaction
from apps.payments.services import InsufficientFunds, apply_transaction
from apps.vehicles.models import Vehicle

from .models import BLOCKING_STATUSES, Booking
from .pricing import billable_hours, cancellation_fee, platform_share, rental_amount
from .terms import TERMS_VERSION

Kind = WalletTransaction.Kind


class BookingError(Exception):
    def __init__(self, code, message, status=400, extra=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.extra = extra or {}


def blocked_until_for(end_at):
    return end_at + timedelta(minutes=settings.BOOKING_BUFFER_MINUTES)


def validate_period(start_at, end_at, now=None):
    now = now or timezone.now()
    if start_at < now - timedelta(minutes=2):
        raise BookingError("start_in_past", "The start time is in the past.")
    if start_at > now + timedelta(days=settings.BOOKING_MAX_ADVANCE_DAYS):
        raise BookingError("too_far_ahead", "The start time is too far in the future.")
    if end_at <= start_at:
        raise BookingError("invalid_period", "The end time must be after the start time.")

    duration = end_at - start_at
    if duration < timedelta(hours=settings.BOOKING_MIN_HOURS):
        raise BookingError("duration_too_short", "The minimum rental is one hour.")
    if duration > timedelta(days=settings.BOOKING_MAX_DAYS):
        raise BookingError("duration_too_long", "The rental is too long.")


def is_slot_free(vehicle_id, start_at, blocked_until, exclude_id=None):
    queryset = Booking.objects.filter(
        vehicle_id=vehicle_id,
        status__in=BLOCKING_STATUSES,
        start_at__lt=blocked_until,
        blocked_until__gt=start_at,
    )
    if exclude_id is not None:
        queryset = queryset.exclude(pk=exclude_id)
    return not queryset.exists()


def build_quote(vehicle, start_at, end_at, renter=None, now=None):
    validate_period(start_at, end_at, now)

    if renter is not None and vehicle.owner_id == renter.id:
        raise BookingError("own_vehicle", "You cannot rent your own vehicle.")

    if vehicle.kind == Vehicle.Kind.CAR:
        end_date = timezone.localtime(end_at).date()
        if vehicle.insurance_expiry is None or vehicle.insurance_expiry < end_date:
            raise BookingError(
                "insurance_expired",
                "The vehicle's insurance expires before the end of this rental.",
            )

    hours = billable_hours(start_at, end_at)
    rental = rental_amount(hours, vehicle.price_per_hour, vehicle.price_per_day)
    return {
        "hours": hours,
        "rental_amount": rental,
        "deposit_amount": vehicle.deposit,
        "total": rental + vehicle.deposit,
    }


@transaction.atomic
def create_booking(
    *, renter, vehicle_id, start_at, end_at, terms_version, idempotency_key=None
):
    # A repeated request with the same key returns the first result untouched.
    if idempotency_key:
        existing = Booking.objects.filter(
            renter=renter, idempotency_key=idempotency_key
        ).first()
        if existing:
            return existing, False

    if terms_version != TERMS_VERSION:
        raise BookingError(
            "terms_outdated", "The terms changed. Please read and accept them again."
        )

    # Locking the vehicle row serializes bookings of the same vehicle.
    vehicle = (
        Vehicle.objects.select_for_update()
        .filter(
            pk=vehicle_id,
            approval_status=Vehicle.ApprovalStatus.APPROVED,
            is_active=True,
        )
        .first()
    )
    if vehicle is None:
        raise BookingError("vehicle_not_found", "This vehicle is not available.", 404)

    quote = build_quote(vehicle, start_at, end_at, renter=renter)
    blocked_until = blocked_until_for(end_at)
    if not is_slot_free(vehicle.pk, start_at, blocked_until):
        raise BookingError("slot_taken", "This time is already booked.", 409)

    try:
        # The savepoint lets us handle a database-level overlap rejection.
        with transaction.atomic():
            booking = Booking.objects.create(
                renter=renter,
                vehicle=vehicle,
                start_at=start_at,
                end_at=end_at,
                blocked_until=blocked_until,
                hours=quote["hours"],
                price_per_hour=vehicle.price_per_hour,
                price_per_day=vehicle.price_per_day,
                rental_amount=quote["rental_amount"],
                deposit_amount=quote["deposit_amount"],
                total_paid=quote["total"],
                deposit_status=(
                    Booking.DepositStatus.HELD
                    if quote["deposit_amount"]
                    else Booking.DepositStatus.NONE
                ),
                terms_version=terms_version,
                terms_accepted_at=timezone.now(),
                idempotency_key=idempotency_key,
            )
    except IntegrityError:
        if idempotency_key:
            existing = Booking.objects.filter(
                renter=renter, idempotency_key=idempotency_key
            ).first()
            if existing:
                return existing, False
        raise BookingError("slot_taken", "This time is already booked.", 409)

    try:
        apply_transaction(
            renter,
            -quote["rental_amount"],
            Kind.BOOKING_CHARGE,
            reference=f"booking:{booking.pk}",
            idempotency_key=f"booking-{booking.pk}-charge",
        )
        if quote["deposit_amount"]:
            apply_transaction(
                renter,
                -quote["deposit_amount"],
                Kind.DEPOSIT_HOLD,
                reference=f"booking:{booking.pk}",
                idempotency_key=f"booking-{booking.pk}-deposit",
            )
    except InsufficientFunds as exc:
        # Raising here rolls back the whole transaction, including the booking.
        raise BookingError(
            "insufficient_funds",
            "Your wallet balance is not enough.",
            402,
            {"balance": exc.balance, "required": quote["total"]},
        )

    return booking, True


@transaction.atomic
def cancel_booking(*, booking_id, user, reason=""):
    booking = (
        Booking.objects.select_for_update(of=("self",))
        .select_related("vehicle", "vehicle__owner", "renter")
        .filter(pk=booking_id)
        .first()
    )
    if booking is None:
        raise BookingError("not_found", "Booking not found.", 404)

    is_renter = booking.renter_id == user.id
    is_owner = booking.vehicle.owner_id == user.id
    if not (is_renter or is_owner):
        raise BookingError("not_found", "Booking not found.", 404)

    if booking.status != Booking.Status.CONFIRMED:
        raise BookingError("not_cancellable", "This booking cannot be cancelled.", 409)

    now = timezone.now()
    if now >= booking.start_at:
        raise BookingError(
            "already_started", "The rental has already started.", 409
        )

    # A cancellation by the owner is always free for the renter.
    fee = 0
    if is_renter:
        fee = cancellation_fee(
            rental_amount=booking.rental_amount,
            price_per_day=booking.price_per_day,
            start_at=booking.start_at,
            now=now,
        )
    refund = booking.total_paid - fee
    platform_fee = platform_share(fee)

    if refund > 0:
        apply_transaction(
            booking.renter,
            refund,
            Kind.REFUND,
            reference=f"booking:{booking.pk}",
            idempotency_key=f"booking-{booking.pk}-refund",
        )
    if fee - platform_fee > 0:
        apply_transaction(
            booking.vehicle.owner,
            fee - platform_fee,
            Kind.PAYOUT,
            reference=f"booking:{booking.pk}",
            idempotency_key=f"booking-{booking.pk}-payout",
        )

    booking.status = Booking.Status.CANCELLED
    booking.cancelled_at = now
    booking.cancelled_by = "renter" if is_renter else "owner"
    booking.cancel_reason = reason
    booking.cancellation_fee = fee
    booking.refund_amount = refund
    booking.platform_fee = platform_fee
    booking.deposit_status = (
        Booking.DepositStatus.RELEASED
        if booking.deposit_amount
        else Booking.DepositStatus.NONE
    )
    booking.save()
    return booking
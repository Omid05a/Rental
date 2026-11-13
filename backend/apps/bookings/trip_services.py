from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from apps.payments.models import WalletTransaction
from apps.payments.services import InsufficientFunds, apply_transaction
from apps.vehicles.models import Vehicle

from .models import Booking, DamageReport, InspectionPhoto
from .pricing import (
    billable_late_minutes,
    fuel_fee_amount,
    late_fee_amount,
    platform_share,
    rental_amount,
)
from .services import BookingError, blocked_until_for, is_slot_free
from .trips import distance_m, qr_matches, required_angles

Kind = WalletTransaction.Kind
Phase = InspectionPhoto.Phase


def get_locked_booking(booking_id, user):
    booking = (
        Booking.objects.select_for_update(of=("self",))
        .select_related("vehicle", "vehicle__owner", "renter")
        .filter(pk=booking_id)
        .first()
    )
    if booking is None or user.id not in (booking.renter_id, booking.vehicle.owner_id):
        raise BookingError("not_found", "Booking not found.", 404)
    return booking


def require_renter(booking, user):
    if booking.renter_id != user.id:
        raise BookingError("forbidden", "Only the renter can do this.", 403)


def require_owner(booking, user):
    if booking.vehicle.owner_id != user.id:
        raise BookingError("forbidden", "Only the owner can do this.", 403)


def start_window_opens(booking):
    return booking.start_at - timedelta(minutes=settings.TRIP_EARLY_START_MINUTES)


def missing_angles(booking, phase):
    taken = set(
        booking.photos.filter(phase=phase).values_list("angle", flat=True)
    )
    return [a for a in required_angles(booking.vehicle.kind) if a not in taken]


def check_near_vehicle(vehicle, latitude, longitude):
    distance = distance_m(latitude, longitude, vehicle.latitude, vehicle.longitude)
    limit = vehicle.pickup_radius_m + settings.TRIP_RADIUS_TOLERANCE_M
    return distance, limit


# ---------------------------------------------------------------- photos


@transaction.atomic
def save_photo(
    *, booking_id, user, phase, angle, image, latitude=None, longitude=None
):
    booking = get_locked_booking(booking_id, user)
    now = timezone.now()

    if phase == Phase.DAMAGE:
        require_owner(booking, user)
        report = DamageReport.objects.filter(booking=booking).first()
        if report is None or report.status != DamageReport.Status.OPEN:
            raise BookingError(
                "no_open_report", "There is no open damage report.", 409
            )
        if angle != InspectionPhoto.Angle.DAMAGE:
            raise BookingError("invalid_angle", "Use the damage angle for evidence photos.")
        count = booking.photos.filter(phase=Phase.DAMAGE).count()
        if count >= settings.MAX_DAMAGE_PHOTOS:
            raise BookingError("too_many_photos", "Too many evidence photos.")
        return InspectionPhoto.objects.create(
            booking=booking,
            phase=phase,
            angle=angle,
            image=image,
            latitude=latitude,
            longitude=longitude,
        )

    require_renter(booking, user)
    if angle not in required_angles(booking.vehicle.kind):
        raise BookingError("invalid_angle", "This angle is not used for this vehicle.")

    if phase == Phase.START:
        if booking.status != Booking.Status.CONFIRMED:
            raise BookingError("not_startable", "This booking cannot be started.", 409)
        if now < start_window_opens(booking):
            raise BookingError("too_early", "It is too early to start this rental.", 409)
        if now > booking.end_at:
            raise BookingError("too_late", "The rental period is over.", 409)
    else:
        if booking.status != Booking.Status.ACTIVE:
            raise BookingError("not_active", "The rental is not in progress.", 409)

    existing = booking.photos.filter(phase=phase, angle=angle).first()
    if existing:
        existing.image.delete(save=False)
        existing.image = image
        existing.latitude = latitude
        existing.longitude = longitude
        existing.taken_at = now
        existing.save()
        return existing

    return InspectionPhoto.objects.create(
        booking=booking,
        phase=phase,
        angle=angle,
        image=image,
        latitude=latitude,
        longitude=longitude,
        taken_at=now,
    )


# ------------------------------------------------------------ start / end


@transaction.atomic
def start_trip(*, booking_id, user, qr_code, latitude, longitude, fuel_percent=None):
    booking = get_locked_booking(booking_id, user)
    require_renter(booking, user)
    if booking.status != Booking.Status.CONFIRMED:
        raise BookingError("not_startable", "This booking cannot be started.", 409)

    now = timezone.now()
    opens_at = start_window_opens(booking)
    if now < opens_at:
        raise BookingError(
            "too_early",
            "It is too early to start this rental.",
            409,
            {"opens_at": opens_at.isoformat()},
        )
    if now > booking.end_at:
        raise BookingError("too_late", "The rental period is over.", 409)

    vehicle = booking.vehicle
    if Booking.objects.filter(
        vehicle=vehicle, status=Booking.Status.ACTIVE
    ).exists():
        raise BookingError(
            "vehicle_in_use", "The vehicle has not been returned yet.", 409
        )

    missing = missing_angles(booking, Phase.START)
    if missing:
        raise BookingError(
            "inspection_incomplete",
            "Take all the required photos first.",
            400,
            {"missing": missing},
        )

    if not qr_matches(vehicle.pk, qr_code):
        raise BookingError(
            "invalid_qr", "The QR code does not match this vehicle.", 400
        )

    distance, limit = check_near_vehicle(vehicle, latitude, longitude)
    if distance > limit:
        raise BookingError(
            "too_far",
            "You are too far from the vehicle.",
            400,
            {"distance_m": round(distance), "limit_m": limit},
        )

    if vehicle.kind == Vehicle.Kind.CAR:
        if fuel_percent is None:
            raise BookingError("fuel_required", "Enter the fuel or charge level.")
    else:
        fuel_percent = None

    booking.status = Booking.Status.ACTIVE
    booking.started_at = now
    booking.start_fuel_percent = fuel_percent
    booking.save(update_fields=["status", "started_at", "start_fuel_percent"])
    return booking


@transaction.atomic
def extend_trip(*, booking_id, user, hours, idempotency_key=None):
    # Lock the vehicle first, in the same order as create_booking.
    vehicle_id = (
        Booking.objects.filter(pk=booking_id)
        .values_list("vehicle_id", flat=True)
        .first()
    )
    if vehicle_id is None:
        raise BookingError("not_found", "Booking not found.", 404)
    Vehicle.objects.select_for_update().filter(pk=vehicle_id).first()

    booking = get_locked_booking(booking_id, user)
    require_renter(booking, user)
    if booking.status != Booking.Status.ACTIVE:
        raise BookingError(
            "not_active", "Only a rental in progress can be extended.", 409
        )

    # A retry of the last extension changes nothing.
    if idempotency_key and booking.last_extension_key == idempotency_key:
        return booking

    now = timezone.now()
    new_end = booking.end_at + timedelta(hours=hours)
    if new_end <= now:
        raise BookingError(
            "extension_too_short",
            "The extension does not cover the time already used.",
        )
    if new_end - booking.start_at > timedelta(days=settings.BOOKING_MAX_DAYS):
        raise BookingError("duration_too_long", "The rental is too long.")

    vehicle = booking.vehicle
    if vehicle.kind == Vehicle.Kind.CAR:
        end_date = timezone.localtime(new_end).date()
        if vehicle.insurance_expiry is None or vehicle.insurance_expiry < end_date:
            raise BookingError(
                "insurance_expired",
                "The vehicle's insurance expires before the new end time.",
            )

    blocked_until = blocked_until_for(new_end)
    if not is_slot_free(
        vehicle.pk, booking.start_at, blocked_until, exclude_id=booking.pk
    ):
        raise BookingError(
            "extension_blocked",
            "The vehicle is booked right after your rental.",
            409,
        )

    new_hours = booking.hours + hours
    new_rental = rental_amount(
        new_hours, booking.price_per_hour, booking.price_per_day
    )
    extra = new_rental - booking.rental_amount

    try:
        if extra > 0:
            apply_transaction(
                booking.renter,
                -extra,
                Kind.BOOKING_CHARGE,
                reference=f"booking:{booking.pk}",
                idempotency_key=(
                    f"booking-{booking.pk}-extend-{idempotency_key}"
                    if idempotency_key
                    else None
                ),
            )
    except InsufficientFunds as exc:
        raise BookingError(
            "insufficient_funds",
            "Your wallet balance is not enough.",
            402,
            {"balance": exc.balance, "required": extra},
        )

    try:
        with transaction.atomic():
            booking.end_at = new_end
            booking.blocked_until = blocked_until
            booking.hours = new_hours
            booking.rental_amount = new_rental
            booking.total_paid = booking.total_paid + extra
            booking.last_extension_key = idempotency_key or ""
            booking.save(
                update_fields=[
                    "end_at",
                    "blocked_until",
                    "hours",
                    "rental_amount",
                    "total_paid",
                    "last_extension_key",
                ]
            )
    except IntegrityError:
        # The wallet charge above is rolled back with the outer transaction.
        raise BookingError(
            "extension_blocked",
            "The vehicle is booked right after your rental.",
            409,
        )
    return booking


@transaction.atomic
def end_trip(*, booking_id, user, latitude, longitude, fuel_percent=None):
    booking = get_locked_booking(booking_id, user)
    require_renter(booking, user)
    if booking.status != Booking.Status.ACTIVE:
        raise BookingError("not_active", "The rental is not in progress.", 409)

    vehicle = booking.vehicle
    missing = missing_angles(booking, Phase.END)
    if missing:
        raise BookingError(
            "inspection_incomplete",
            "Take all the required photos first.",
            400,
            {"missing": missing},
        )

    distance, limit = check_near_vehicle(vehicle, latitude, longitude)
    if distance > limit:
        raise BookingError(
            "outside_return_area",
            "Return the vehicle to its pickup location first.",
            400,
            {"distance_m": round(distance), "limit_m": limit},
        )

    if vehicle.kind == Vehicle.Kind.CAR:
        if fuel_percent is None:
            raise BookingError("fuel_required", "Enter the fuel or charge level.")
    else:
        fuel_percent = None

    now = timezone.now()
    late_minutes = billable_late_minutes(booking.end_at, now)
    late_fee = late_fee_amount(late_minutes, booking.price_per_hour)
    fuel_fee = fuel_fee_amount(booking.start_fuel_percent, fuel_percent)

    # Fees are collected from the deposit, never beyond it.
    available = booking.deposit_amount
    late_fee = min(late_fee, available)
    available -= late_fee
    fuel_fee = min(fuel_fee, available)

    owner_gross = booking.rental_amount + late_fee + fuel_fee
    platform_fee = platform_share(owner_gross)
    apply_transaction(
        vehicle.owner,
        owner_gross - platform_fee,
        Kind.PAYOUT,
        reference=f"booking:{booking.pk}",
        idempotency_key=f"booking-{booking.pk}-trip-payout",
    )

    booking.status = Booking.Status.COMPLETED
    booking.ended_at = now
    booking.end_fuel_percent = fuel_percent
    booking.late_minutes = late_minutes
    booking.late_fee = late_fee
    booking.fuel_fee = fuel_fee
    booking.platform_fee = platform_fee
    booking.deposit_status = (
        Booking.DepositStatus.HELD
        if booking.deposit_amount
        else Booking.DepositStatus.NONE
    )
    booking.deposit_release_at = now + timedelta(hours=settings.DAMAGE_WINDOW_HOURS)
    booking.save()
    return booking


# --------------------------------------------------------------- deposit


@transaction.atomic
def _release_deposit(booking_id):
    booking = (
        Booking.objects.select_for_update(of=("self",))
        .select_related("renter")
        .filter(
            pk=booking_id,
            status=Booking.Status.COMPLETED,
            deposit_status=Booking.DepositStatus.HELD,
        )
        .first()
    )
    if booking is None:
        return False
    if DamageReport.objects.filter(
        booking=booking, status=DamageReport.Status.OPEN
    ).exists():
        return False

    remaining = booking.deposit_remaining
    if remaining > 0:
        apply_transaction(
            booking.renter,
            remaining,
            Kind.REFUND,
            reference=f"booking:{booking.pk}",
            idempotency_key=f"booking-{booking.pk}-deposit-release",
        )
    booking.deposit_status = Booking.DepositStatus.RELEASED
    booking.save(update_fields=["deposit_status"])
    return True


def release_due_deposits(*, now=None, user=None):
    """Returns deposits whose damage-report window has passed without a claim.

    Called when bookings are viewed and by the release_deposits command."""
    now = now or timezone.now()
    queryset = Booking.objects.filter(
        status=Booking.Status.COMPLETED,
        deposit_status=Booking.DepositStatus.HELD,
        deposit_release_at__lte=now,
    ).exclude(damage_report__status=DamageReport.Status.OPEN)
    if user is not None:
        queryset = queryset.filter(Q(renter=user) | Q(vehicle__owner=user))

    released = 0
    for booking_id in list(queryset.values_list("pk", flat=True)):
        if _release_deposit(booking_id):
            released += 1
    return released


# ---------------------------------------------------------------- damage


@transaction.atomic
def create_damage_report(*, booking_id, user, description, claimed_amount):
    booking = get_locked_booking(booking_id, user)
    require_owner(booking, user)

    now = timezone.now()
    if (
        booking.status != Booking.Status.COMPLETED
        or booking.deposit_status != Booking.DepositStatus.HELD
        or booking.deposit_release_at is None
        or now > booking.deposit_release_at
    ):
        raise BookingError(
            "report_closed", "The damage report period has ended.", 409
        )
    if DamageReport.objects.filter(booking=booking).exists():
        raise BookingError("already_reported", "A report already exists.", 409)

    remaining = booking.deposit_remaining
    if remaining <= 0:
        raise BookingError("no_deposit_left", "No deposit is left to claim.", 409)
    if claimed_amount > remaining:
        raise BookingError(
            "claim_too_high",
            "The claim is more than the remaining deposit.",
            400,
            {"max": remaining},
        )

    return DamageReport.objects.create(
        booking=booking, description=description, claimed_amount=claimed_amount
    )


@transaction.atomic
def respond_damage(*, booking_id, user, note):
    booking = get_locked_booking(booking_id, user)
    require_renter(booking, user)
    report = DamageReport.objects.filter(booking=booking).first()
    if report is None or report.status != DamageReport.Status.OPEN:
        raise BookingError("no_open_report", "There is no open damage report.", 409)
    report.renter_response = note
    report.save(update_fields=["renter_response"])
    return report


@transaction.atomic
def resolve_damage(*, report_id, approved_amount, note=""):
    """Settles the deposit: approved amount to the owner, the rest to the renter."""
    report = (
        DamageReport.objects.select_for_update(of=("self",))
        .select_related("booking", "booking__renter", "booking__vehicle__owner")
        .get(pk=report_id)
    )
    if report.status != DamageReport.Status.OPEN:
        raise BookingError("already_resolved", "This report is already resolved.", 409)

    booking = report.booking
    remaining = booking.deposit_remaining
    if approved_amount < 0 or approved_amount > remaining:
        raise BookingError(
            "invalid_amount",
            f"The amount must be between 0 and {remaining}.",
            400,
        )

    if approved_amount > 0:
        share = platform_share(approved_amount)
        apply_transaction(
            booking.vehicle.owner,
            approved_amount - share,
            Kind.PAYOUT,
            reference=f"damage:{report.pk}",
            idempotency_key=f"damage-{report.pk}-payout",
        )
        booking.platform_fee += share

    refund = remaining - approved_amount
    if refund > 0:
        apply_transaction(
            booking.renter,
            refund,
            Kind.REFUND,
            reference=f"damage:{report.pk}",
            idempotency_key=f"damage-{report.pk}-refund",
        )

    booking.damage_deduction = approved_amount
    booking.deposit_status = Booking.DepositStatus.RELEASED
    booking.save(
        update_fields=["damage_deduction", "deposit_status", "platform_fee"]
    )

    report.status = DamageReport.Status.RESOLVED
    report.approved_amount = approved_amount
    report.resolution_note = note
    report.resolved_at = timezone.now()
    report.save()
    return report
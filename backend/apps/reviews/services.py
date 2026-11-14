from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count
from django.utils import timezone

from apps.bookings.models import Booking
from apps.bookings.services import BookingError

from .models import Review

Direction = Review.Direction


def review_deadline(booking):
    if booking.ended_at is None:
        return None
    return booking.ended_at + timedelta(days=settings.REVIEW_WINDOW_DAYS)


def role_of(booking, user):
    if booking.renter_id == user.id:
        return "renter"
    if booking.vehicle.owner_id == user.id:
        return "owner"
    return None


def get_participant_booking(booking_id, user, lock=False):
    queryset = Booking.objects.select_related("vehicle", "vehicle__owner", "renter")
    if lock:
        queryset = queryset.select_for_update(of=("self",))
    booking = queryset.filter(pk=booking_id).first()
    if booking is None or role_of(booking, user) is None:
        raise BookingError("not_found", "Booking not found.", 404)
    return booking


def rating_summary(queryset):
    result = queryset.order_by().aggregate(avg=Avg("rating"), count=Count("id"))
    avg = round(result["avg"], 1) if result["avg"] is not None else None
    return {"avg": avg, "count": result["count"]}


def _serialize(review):
    return {
        "id": review.pk,
        "rating": review.rating,
        "comment": review.comment,
        "created_at": review.created_at,
    }


def review_state(booking, user, now=None):
    """What the user may see and do about the reviews of one booking.

    The other side's review stays hidden until the user has written theirs (or
    the review period ended), so nobody can answer a review with revenge."""
    now = now or timezone.now()
    role = role_of(booking, user)
    deadline = review_deadline(booking)
    closed = deadline is not None and now > deadline

    mine = Review.objects.filter(booking=booking, author=user).first()
    theirs = Review.objects.filter(booking=booking).exclude(author=user).first()

    if role == "renter":
        other = booking.vehicle.owner
        other_reviews = Review.objects.filter(
            subject=other, direction=Direction.RENTER_TO_OWNER
        )
    else:
        other = booking.renter
        other_reviews = Review.objects.filter(
            subject=other, direction=Direction.OWNER_TO_RENTER
        )

    can_review = (
        booking.status == Booking.Status.COMPLETED
        and mine is None
        and not closed
    )

    return {
        "role": role,
        "can_review": can_review,
        "closed": closed,
        "deadline": deadline,
        "counterpart_name": other.first_name,
        "counterpart_rating": rating_summary(other_reviews),
        "mine": _serialize(mine) if mine else None,
        "theirs": _serialize(theirs) if theirs and (mine or closed) else None,
    }


@transaction.atomic
def create_review(*, booking_id, user, rating, comment=""):
    booking = get_participant_booking(booking_id, user, lock=True)

    if booking.status != Booking.Status.COMPLETED:
        raise BookingError(
            "not_completed", "Only a completed trip can be reviewed.", 409
        )
    deadline = review_deadline(booking)
    if deadline is not None and timezone.now() > deadline:
        raise BookingError("review_closed", "The review period has ended.", 409)

    if role_of(booking, user) == "renter":
        subject = booking.vehicle.owner
        direction = Direction.RENTER_TO_OWNER
    else:
        subject = booking.renter
        direction = Direction.OWNER_TO_RENTER

    try:
        with transaction.atomic():
            return Review.objects.create(
                booking=booking,
                author=user,
                subject=subject,
                direction=direction,
                rating=rating,
                comment=comment.strip(),
            )
    except IntegrityError:
        raise BookingError(
            "already_reviewed", "You already reviewed this trip.", 409
        )


def vehicle_reviews(vehicle_id, limit=20):
    queryset = Review.objects.filter(
        direction=Direction.RENTER_TO_OWNER, booking__vehicle_id=vehicle_id
    ).select_related("author")
    items = [
        {
            "id": review.pk,
            "rating": review.rating,
            "comment": review.comment,
            "author_first_name": review.author.first_name,
            "created_at": review.created_at,
        }
        for review in queryset[:limit]
    ]
    return {**rating_summary(queryset), "results": items}


def vehicle_ratings(vehicle_ids):
    rows = (
        Review.objects.filter(
            direction=Direction.RENTER_TO_OWNER, booking__vehicle_id__in=vehicle_ids
        )
        .order_by()
        .values("booking__vehicle_id")
        .annotate(avg=Avg("rating"), count=Count("id"))
    )
    return {
        str(row["booking__vehicle_id"]): {
            "avg": round(row["avg"], 1),
            "count": row["count"],
        }
        for row in rows
    }
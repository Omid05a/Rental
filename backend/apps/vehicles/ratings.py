from django.db.models import (
    Avg,
    Count,
    FloatField,
    IntegerField,
    OuterRef,
    Subquery,
)
from django.db.models.functions import Coalesce


def with_ratings(queryset):
    """Adds rating_avg and rating_count: the reviews renters wrote about the
    owner after trips with each vehicle."""
    from apps.reviews.models import Review

    stats = (
        Review.objects.filter(
            direction=Review.Direction.RENTER_TO_OWNER,
            booking__vehicle=OuterRef("pk"),
        )
        .order_by()
        .values("booking__vehicle")
        .annotate(avg=Avg("rating"), count=Count("id"))
    )
    return queryset.annotate(
        rating_avg=Subquery(stats.values("avg")[:1], output_field=FloatField()),
        rating_count=Coalesce(
            Subquery(stats.values("count")[:1], output_field=IntegerField()), 0
        ),
    )
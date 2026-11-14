from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Review(models.Model):
    class Direction(models.TextChoices):
        RENTER_TO_OWNER = "renter_to_owner", "Renter reviews owner"
        OWNER_TO_RENTER = "owner_to_renter", "Owner reviews renter"

    booking = models.ForeignKey(
        "bookings.Booking", on_delete=models.CASCADE, related_name="reviews"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews_written",
    )
    subject = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews_received",
    )
    direction = models.CharField(max_length=20, choices=Direction.choices)
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["subject", "direction"], name="review_subject_idx")
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["booking", "author"], name="review_one_per_author"
            ),
            models.CheckConstraint(
                condition=Q(rating__gte=1) & Q(rating__lte=5),
                name="review_rating_range",
            ),
        ]

    def __str__(self):
        return f"{self.direction} {self.rating}/5 (booking {self.booking_id})"
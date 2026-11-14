from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Notification(models.Model):
    class Kind(models.TextChoices):
        VERIFICATION = "verification", "Identity verification"
        VEHICLE = "vehicle", "Vehicle review"
        BOOKING = "booking", "Booking"
        TRIP = "trip", "Trip"
        PAYMENT = "payment", "Payment"
        DAMAGE = "damage", "Damage report"
        REVIEW = "review", "Review"
        REMINDER = "reminder", "Reminder"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    title = models.CharField(max_length=120)
    body = models.TextField(blank=True)
    link = models.CharField(max_length=120, blank=True)
    # A key that stops the same event from notifying a user twice.
    dedupe_key = models.CharField(max_length=80, null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "read_at"], name="notification_unread_idx")
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "dedupe_key"],
                condition=Q(dedupe_key__isnull=False),
                name="notification_dedupe",
            )
        ]

    def __str__(self):
        return f"{self.kind}: {self.title}"
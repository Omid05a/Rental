from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.notifications.models import Notification
from apps.notifications.services import notify

from .models import Review


@receiver(post_save, sender=Review)
def notify_review_received(sender, instance, created, raw=False, **kwargs):
    if raw or not created:
        return
    # The text is neutral on purpose: the review itself stays hidden until the
    # receiver writes their own.
    notify(
        instance.subject,
        Notification.Kind.REVIEW,
        "برای شما نظر جدیدی ثبت شد",
        "بعد از ثبت نظر خودتان درباره این سفر، نظر طرف مقابل نمایش داده می‌شود.",
        f"/bookings/{instance.booking_id}",
        f"review-{instance.pk}",
    )
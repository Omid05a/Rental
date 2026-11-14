from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.notifications.models import Notification
from apps.notifications.services import notify

from .models import Vehicle


@receiver(pre_save, sender=Vehicle)
def remember_approval_status(sender, instance, **kwargs):
    update_fields = kwargs.get("update_fields")
    if not instance.pk or (
        update_fields is not None and "approval_status" not in update_fields
    ):
        instance._previous_approval = None
        return
    instance._previous_approval = (
        Vehicle.objects.filter(pk=instance.pk)
        .values_list("approval_status", flat=True)
        .first()
    )


@receiver(post_save, sender=Vehicle)
def notify_vehicle_decision(sender, instance, created, raw=False, **kwargs):
    previous = getattr(instance, "_previous_approval", None)
    if raw or created or previous is None:
        return
    if previous == instance.approval_status:
        return

    link = f"/vehicles/mine/{instance.pk}"
    Status = Vehicle.ApprovalStatus
    if instance.approval_status == Status.APPROVED:
        notify(
            instance.owner,
            Notification.Kind.VEHICLE,
            "وسیله شما تأیید شد",
            f"«{instance.title}» حالا در جستجو نمایش داده می‌شود.",
            link,
        )
    elif instance.approval_status == Status.REJECTED:
        reason = instance.rejection_reason or "دلیل مشخص نشده است."
        notify(
            instance.owner,
            Notification.Kind.VEHICLE,
            "وسیله شما تأیید نشد",
            f"«{instance.title}»: {reason}",
            link,
        )
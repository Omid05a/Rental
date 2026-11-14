from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.notifications.models import Notification
from apps.notifications.services import notify

from .models import User


@receiver(pre_save, sender=User)
def remember_verification_status(sender, instance, **kwargs):
    update_fields = kwargs.get("update_fields")
    if not instance.pk or (
        update_fields is not None and "verification_status" not in update_fields
    ):
        instance._previous_verification = None
        return
    instance._previous_verification = (
        User.objects.filter(pk=instance.pk)
        .values_list("verification_status", flat=True)
        .first()
    )


@receiver(post_save, sender=User)
def notify_verification_decision(sender, instance, created, raw=False, **kwargs):
    previous = getattr(instance, "_previous_verification", None)
    if raw or created or previous is None:
        return
    if previous == instance.verification_status:
        return

    Status = User.VerificationStatus
    if instance.verification_status == Status.APPROVED:
        notify(
            instance,
            Notification.Kind.VERIFICATION,
            "هویت شما تأیید شد",
            "حالا می‌توانید وسیله اجاره کنید یا وسیله خودتان را ثبت کنید.",
            "/profile",
        )
    elif instance.verification_status == Status.REJECTED:
        reason = instance.rejection_reason or "دلیل مشخص نشده است."
        notify(
            instance,
            Notification.Kind.VERIFICATION,
            "مدارک شما تأیید نشد",
            f"دلیل: {reason} مدارک را اصلاح و دوباره ارسال کنید.",
            "/verification",
        )
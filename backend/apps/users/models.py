import os
import uuid

from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError("Phone number is required")
        user = self.model(phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class VerificationStatus(models.TextChoices):
        NOT_SUBMITTED = "not_submitted", "Not submitted"
        PENDING = "pending", "Pending review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    phone = models.CharField(max_length=15, unique=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.NOT_SUBMITTED,
    )
    rejection_reason = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.phone


class OTPCode(models.Model):
    """One-time password sent to a phone number for login."""

    phone = models.CharField(max_length=15, db_index=True)
    code_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.phone} ({self.created_at:%Y-%m-%d %H:%M})"


def private_storage():
    """Storage outside MEDIA_ROOT: files here are never served publicly."""
    return FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT)


def document_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        ext = ".jpg"
    return f"documents/{instance.user_id}/{instance.doc_type}-{uuid.uuid4().hex}{ext}"


class VerificationDocument(models.Model):
    """An identity document image uploaded by a user (one per type)."""

    class DocType(models.TextChoices):
        NATIONAL_CARD_FRONT = "national_card_front", "National card (front)"
        NATIONAL_CARD_BACK = "national_card_back", "National card (back)"
        DRIVER_LICENSE = "driver_license", "Driver license"
        SELFIE = "selfie", "Selfie with national card"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    doc_type = models.CharField(max_length=30, choices=DocType.choices)
    file = models.ImageField(upload_to=document_upload_path, storage=private_storage)
    uploaded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["user_id", "doc_type"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "doc_type"], name="unique_document_per_type"
            )
        ]

    def __str__(self):
        return f"{self.user_id} - {self.doc_type}"
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Wallet(models.Model):
    """A virtual wallet. Amounts are whole Toman."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallet",
    )
    balance = models.BigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(balance__gte=0), name="wallet_balance_not_negative"
            )
        ]

    def __str__(self):
        return f"Wallet of {self.user_id}: {self.balance}"


class WalletTransaction(models.Model):
    """One entry in the wallet ledger. Positive amounts add money."""

    class Kind(models.TextChoices):
        TOPUP = "topup", "Top-up"
        BOOKING_CHARGE = "booking_charge", "Booking charge"
        DEPOSIT_HOLD = "deposit_hold", "Deposit hold"
        REFUND = "refund", "Refund"
        PAYOUT = "payout", "Payout"

    wallet = models.ForeignKey(
        Wallet, on_delete=models.CASCADE, related_name="transactions"
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    amount = models.BigIntegerField()
    balance_after = models.BigIntegerField()
    reference = models.CharField(max_length=60, blank=True)
    idempotency_key = models.CharField(max_length=64, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["wallet", "idempotency_key"],
                condition=Q(idempotency_key__isnull=False),
                name="wallet_transaction_idempotent",
            )
        ]

    def __str__(self):
        return f"{self.kind} {self.amount}"
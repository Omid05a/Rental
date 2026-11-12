from django.db import transaction

from .models import Wallet, WalletTransaction


class InsufficientFunds(Exception):
    def __init__(self, balance, required):
        super().__init__("Insufficient wallet balance.")
        self.balance = balance
        self.required = required


def get_or_create_wallet(user):
    wallet, _ = Wallet.objects.get_or_create(user=user)
    return wallet


@transaction.atomic
def apply_transaction(user, amount, kind, *, reference="", idempotency_key=None):
    """Adds a signed amount to the user's wallet and records it in the ledger.

    The wallet row is locked, so concurrent calls cannot overspend. When an
    idempotency key was already used, the earlier transaction is returned and
    nothing is applied a second time.
    """
    wallet = get_or_create_wallet(user)
    wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

    if idempotency_key:
        existing = WalletTransaction.objects.filter(
            wallet=wallet, idempotency_key=idempotency_key
        ).first()
        if existing:
            return existing

    new_balance = wallet.balance + amount
    if new_balance < 0:
        raise InsufficientFunds(balance=wallet.balance, required=-amount)

    wallet.balance = new_balance
    wallet.save(update_fields=["balance", "updated_at"])
    return WalletTransaction.objects.create(
        wallet=wallet,
        kind=kind,
        amount=amount,
        balance_after=new_balance,
        reference=reference,
        idempotency_key=idempotency_key,
    )
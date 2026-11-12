from django.core.management.base import BaseCommand

from apps.payments.models import WalletTransaction
from apps.payments.services import apply_transaction, get_or_create_wallet
from apps.users.models import User

DEMO_PHONE = "09100000002"
DEMO_FUNDS = 20_000_000


class Command(BaseCommand):
    help = "Creates a verified demo renter (09100000002) with a funded wallet."

    def handle(self, *args, **options):
        user = User.objects.filter(phone=DEMO_PHONE).first()
        if user is None:
            user = User.objects.create_user(
                phone=DEMO_PHONE,
                first_name="رضا",
                last_name="کریمی",
                verification_status=User.VerificationStatus.APPROVED,
            )

        wallet = get_or_create_wallet(user)
        if wallet.balance < DEMO_FUNDS:
            apply_transaction(
                user,
                DEMO_FUNDS - wallet.balance,
                WalletTransaction.Kind.TOPUP,
                reference="seed",
            )

        self.stdout.write(
            self.style.SUCCESS(f"Demo renter {DEMO_PHONE} is ready with a funded wallet.")
        )
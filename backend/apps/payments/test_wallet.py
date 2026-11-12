from django.test import TestCase
from rest_framework.test import APITestCase

from apps.users.models import User
from apps.vehicles.test_api import auth_header, make_user

from .models import Wallet, WalletTransaction
from .services import InsufficientFunds, apply_transaction


class WalletApiTests(APITestCase):
    def setUp(self):
        self.user = make_user("09120000000")
        self.auth = auth_header(self.user)

    def topup(self, amount, key=None):
        headers = dict(self.auth)
        if key:
            headers["HTTP_IDEMPOTENCY_KEY"] = key
        return self.client.post(
            "/api/wallet/topup/", {"amount": amount}, format="json", **headers
        )

    def test_wallet_requires_authentication(self):
        self.assertEqual(self.client.get("/api/wallet/").status_code, 401)

    def test_topup_increases_balance(self):
        response = self.topup(500_000)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["balance"], 500_000)

        wallet = self.client.get("/api/wallet/", **self.auth)
        self.assertEqual(wallet.data["balance"], 500_000)
        self.assertEqual(len(wallet.data["transactions"]), 1)

    def test_same_idempotency_key_credits_once(self):
        self.topup(500_000, key="pay-1")
        again = self.topup(500_000, key="pay-1")
        self.assertEqual(again.data["balance"], 500_000)
        self.assertEqual(WalletTransaction.objects.count(), 1)

    def test_amount_limits(self):
        self.assertEqual(self.topup(5_000).status_code, 400)
        self.assertEqual(self.topup(200_000_000).status_code, 400)


class LedgerTests(TestCase):
    def test_balance_cannot_go_negative(self):
        user = User.objects.create_user(phone="09130000000")
        apply_transaction(user, 100_000, WalletTransaction.Kind.TOPUP)
        with self.assertRaises(InsufficientFunds):
            apply_transaction(user, -200_000, WalletTransaction.Kind.BOOKING_CHARGE)
        self.assertEqual(Wallet.objects.get(user=user).balance, 100_000)
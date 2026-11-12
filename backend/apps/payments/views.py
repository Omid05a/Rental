from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Wallet, WalletTransaction
from .serializers import TopUpSerializer, TransactionSerializer
from .services import apply_transaction, get_or_create_wallet
from .utils import get_idempotency_key


class WalletView(APIView):
    """Balance and the latest ledger entries of the current user."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: None})
    def get(self, request):
        wallet = get_or_create_wallet(request.user)
        transactions = wallet.transactions.all()[:20]
        return Response(
            {
                "balance": wallet.balance,
                "transactions": TransactionSerializer(transactions, many=True).data,
            }
        )


class TopUpView(APIView):
    """Simulated payment gateway: every top-up succeeds."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=TopUpSerializer, responses={200: None})
    def post(self, request):
        serializer = TopUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        transaction = apply_transaction(
            request.user,
            serializer.validated_data["amount"],
            WalletTransaction.Kind.TOPUP,
            reference="simulated-gateway",
            idempotency_key=get_idempotency_key(request),
        )
        balance = Wallet.objects.get(pk=transaction.wallet_id).balance
        return Response(
            {
                "balance": balance,
                "transaction": TransactionSerializer(transaction).data,
            }
        )
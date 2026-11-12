from rest_framework import serializers

from .models import WalletTransaction


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = ("id", "kind", "amount", "balance_after", "reference", "created_at")
        read_only_fields = fields


class TopUpSerializer(serializers.Serializer):
    amount = serializers.IntegerField(min_value=10_000, max_value=100_000_000)
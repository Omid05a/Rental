from django.urls import path

from .views import TopUpView, WalletView

urlpatterns = [
    path("wallet/", WalletView.as_view(), name="wallet"),
    path("wallet/topup/", TopUpView.as_view(), name="wallet-topup"),
]
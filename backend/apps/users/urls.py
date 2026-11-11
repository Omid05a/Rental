from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .verification import (
    DocumentListView,
    DocumentUploadView,
    SubmitVerificationView,
)
from .views import ProfileView, RequestOTPView, VerifyOTPView

urlpatterns = [
    path("auth/request-otp/", RequestOTPView.as_view(), name="request-otp"),
    path("auth/verify-otp/", VerifyOTPView.as_view(), name="verify-otp"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", ProfileView.as_view(), name="profile"),
    path(
        "verification/documents/",
        DocumentListView.as_view(),
        name="verification-documents",
    ),
    path(
        "verification/documents/<str:doc_type>/",
        DocumentUploadView.as_view(),
        name="verification-document-upload",
    ),
    path(
        "verification/submit/",
        SubmitVerificationView.as_view(),
        name="verification-submit",
    ),
]
from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .otp import OTPError, create_otp, verify_otp
from .serializers import (
    ProfileSerializer,
    RequestOTPSerializer,
    UserSerializer,
    VerifyOTPSerializer,
)
from .throttles import (
    OTPRequestIPThrottle,
    OTPRequestPhoneThrottle,
    OTPVerifyIPThrottle,
    OTPVerifyPhoneThrottle,
)


class RequestOTPView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [OTPRequestIPThrottle, OTPRequestPhoneThrottle]

    @extend_schema(request=RequestOTPSerializer, responses={200: None})
    def post(self, request):
        serializer = RequestOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            code = create_otp(serializer.validated_data["phone"])
        except OTPError as exc:
            http_status = (
                status.HTTP_429_TOO_MANY_REQUESTS
                if exc.code == "too_many_requests"
                else status.HTTP_400_BAD_REQUEST
            )
            return Response(
                {"detail": exc.message, "code": exc.code}, status=http_status
            )

        data = {"detail": "Verification code sent."}
        if settings.DEBUG or settings.DEMO_MODE:
            # Demo only: expose the code so the app works without a real
            # SMS provider. Never enable this on a public production server.
            data["dev_code"] = code
        return Response(data)


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [OTPVerifyIPThrottle, OTPVerifyPhoneThrottle]

    @extend_schema(request=VerifyOTPSerializer, responses={200: None})
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]
        try:
            verify_otp(phone, serializer.validated_data["code"])
        except OTPError as exc:
            return Response(
                {"detail": exc.message, "code": exc.code},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(phone=phone).first()
        created = user is None
        if created:
            user = User.objects.create_user(phone=phone)

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
                "is_new_user": created,
            }
        )


class ProfileView(generics.RetrieveUpdateAPIView):
    """Read or update the profile of the logged-in user."""

    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.services import BookingError
from apps.vehicles.models import Vehicle

from .serializers import ReviewCreateSerializer
from .services import (
    create_review,
    get_participant_booking,
    review_state,
    vehicle_ratings,
    vehicle_reviews,
)


def error_response(exc):
    return Response(
        {"detail": exc.message, "code": exc.code, **exc.extra}, status=exc.status
    )


class BookingReviewView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: None})
    def get(self, request, pk):
        try:
            booking = get_participant_booking(pk, request.user)
        except BookingError as exc:
            return error_response(exc)
        return Response(review_state(booking, request.user))

    @extend_schema(request=ReviewCreateSerializer, responses={201: None})
    def post(self, request, pk):
        serializer = ReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            create_review(
                booking_id=pk,
                user=request.user,
                rating=data["rating"],
                comment=data.get("comment", ""),
            )
            booking = get_participant_booking(pk, request.user)
        except BookingError as exc:
            return error_response(exc)
        return Response(review_state(booking, request.user), status=201)


class VehicleReviewsView(APIView):
    """Public reviews of a vehicle's owner, written by its renters."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses={200: None})
    def get(self, request, pk):
        vehicle = get_object_or_404(
            Vehicle,
            pk=pk,
            approval_status=Vehicle.ApprovalStatus.APPROVED,
            is_active=True,
        )
        return Response(vehicle_reviews(vehicle.pk))


class VehicleRatingsView(APIView):
    """Average ratings for several vehicles at once. Query: ids=1,2,3 (max 50)."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses={200: None})
    def get(self, request):
        raw = request.query_params.get("ids", "")
        ids = [int(part) for part in raw.split(",") if part.strip().isdigit()][:50]
        return Response(vehicle_ratings(ids))
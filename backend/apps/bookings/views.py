from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments.services import get_or_create_wallet
from apps.payments.utils import get_idempotency_key
from apps.vehicles.models import Vehicle
from apps.vehicles.permissions import IsVerifiedUser

from .models import BLOCKING_STATUSES, Booking
from .serializers import (
    BookingCreateSerializer,
    BookingSerializer,
    CancelSerializer,
    QuoteRequestSerializer,
)
from .services import (
    BookingError,
    blocked_until_for,
    build_quote,
    cancel_booking,
    create_booking,
    is_slot_free,
)
from .terms import TERMS, TERMS_VERSION


def error_response(exc):
    body = {"detail": exc.message, "code": exc.code, **exc.extra}
    return Response(body, status=exc.status)


def booking_queryset():
    return Booking.objects.select_related(
        "vehicle", "vehicle__owner", "renter"
    ).prefetch_related("vehicle__photos")


def public_vehicle(pk):
    return Vehicle.objects.filter(
        pk=pk, approval_status=Vehicle.ApprovalStatus.APPROVED, is_active=True
    ).first()


class TermsView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses={200: None})
    def get(self, request):
        return Response({"version": TERMS_VERSION, "sections": TERMS})


class BusyView(APIView):
    """Future time ranges in which a vehicle cannot be booked (buffer included)."""

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
        ranges = (
            Booking.objects.filter(
                vehicle=vehicle,
                status__in=BLOCKING_STATUSES,
                blocked_until__gt=timezone.now(),
            )
            .order_by("start_at")
            .values_list("start_at", "blocked_until")
        )
        return Response([{"start": start, "end": end} for start, end in ranges])


class QuoteView(APIView):
    """Price and availability for a period, without creating a booking."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=QuoteRequestSerializer, responses={200: None})
    def post(self, request):
        serializer = QuoteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        vehicle = public_vehicle(data["vehicle"])
        if vehicle is None:
            return Response(
                {"detail": "This vehicle is not available.", "code": "vehicle_not_found"},
                status=404,
            )

        try:
            quote = build_quote(
                vehicle, data["start_at"], data["end_at"], renter=request.user
            )
            if not is_slot_free(
                vehicle.pk, data["start_at"], blocked_until_for(data["end_at"])
            ):
                raise BookingError("slot_taken", "This time is already booked.", 409)
        except BookingError as exc:
            return error_response(exc)

        balance = get_or_create_wallet(request.user).balance
        free_until = data["start_at"] - timedelta(hours=settings.CANCEL_FREE_HOURS)
        return Response(
            {
                **quote,
                "price_per_hour": vehicle.price_per_hour,
                "price_per_day": vehicle.price_per_day,
                "wallet_balance": balance,
                "enough_funds": balance >= quote["total"],
                "free_cancellation_until": free_until,
                "terms_version": TERMS_VERSION,
            }
        )


class BookingListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsVerifiedUser()]
        return [IsAuthenticated()]

    @extend_schema(responses={200: BookingSerializer(many=True)})
    def get(self, request):
        queryset = booking_queryset()
        if request.query_params.get("role") == "owner":
            queryset = queryset.filter(vehicle__owner=request.user)
        else:
            queryset = queryset.filter(renter=request.user)

        status_filter = request.query_params.get("status")
        if status_filter in Booking.Status.values:
            queryset = queryset.filter(status=status_filter)

        serializer = BookingSerializer(
            queryset[:100], many=True, context={"request": request}
        )
        return Response(serializer.data)

    @extend_schema(
        request=BookingCreateSerializer, responses={201: BookingSerializer}
    )
    def post(self, request):
        serializer = BookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            booking, created = create_booking(
                renter=request.user,
                vehicle_id=data["vehicle"],
                start_at=data["start_at"],
                end_at=data["end_at"],
                terms_version=data["terms_version"],
                idempotency_key=get_idempotency_key(request),
            )
        except BookingError as exc:
            return error_response(exc)

        booking = booking_queryset().get(pk=booking.pk)
        return Response(
            BookingSerializer(booking, context={"request": request}).data,
            status=201 if created else 200,
        )


class BookingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: BookingSerializer})
    def get(self, request, pk):
        queryset = booking_queryset().filter(
            Q(renter=request.user) | Q(vehicle__owner=request.user)
        )
        booking = get_object_or_404(queryset, pk=pk)
        return Response(BookingSerializer(booking, context={"request": request}).data)


class BookingCancelView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=CancelSerializer, responses={200: BookingSerializer})
    def post(self, request, pk):
        serializer = CancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            booking = cancel_booking(
                booking_id=pk,
                user=request.user,
                reason=serializer.validated_data.get("reason", ""),
            )
        except BookingError as exc:
            return error_response(exc)

        booking = booking_queryset().get(pk=booking.pk)
        return Response(BookingSerializer(booking, context={"request": request}).data)
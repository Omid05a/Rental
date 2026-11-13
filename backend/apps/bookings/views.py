from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.parsers import MultiPartParser
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
    DamageCreateSerializer,
    DamageRespondSerializer,
    EndTripSerializer,
    ExtendSerializer,
    QuoteRequestSerializer,
    StartTripSerializer,
    TripPhotoSerializer,
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
from .trip_services import (
    create_damage_report,
    end_trip,
    extend_trip,
    release_due_deposits,
    respond_damage,
    save_photo,
    start_trip,
)
from .trips import qr_code_for_vehicle


def error_response(exc):
    body = {"detail": exc.message, "code": exc.code, **exc.extra}
    return Response(body, status=exc.status)


def booking_queryset():
    return (
        Booking.objects.select_related(
            "vehicle", "vehicle__owner", "renter", "damage_report"
        )
        .prefetch_related("vehicle__photos", "photos")
    )


def booking_response(request, booking_id, status=200):
    booking = booking_queryset().get(pk=booking_id)
    data = BookingSerializer(booking, context={"request": request}).data
    return Response(data, status=status)


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
        release_due_deposits(user=request.user)

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

        return booking_response(request, booking.pk, status=201 if created else 200)


class BookingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: BookingSerializer})
    def get(self, request, pk):
        release_due_deposits(user=request.user)
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

        return booking_response(request, booking.pk)


# ------------------------------------------------------------------ trip


class TripPhotoView(APIView):
    """Uploads (or replaces) one inspection or damage photo."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    @extend_schema(request=TripPhotoSerializer, responses={201: None})
    def post(self, request, pk):
        serializer = TripPhotoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            photo = save_photo(
                booking_id=pk,
                user=request.user,
                phase=data["phase"],
                angle=data["angle"],
                image=data["image"],
                latitude=data.get("latitude"),
                longitude=data.get("longitude"),
            )
        except BookingError as exc:
            return error_response(exc)

        return Response(
            {
                "id": photo.pk,
                "phase": photo.phase,
                "angle": photo.angle,
                "image": request.build_absolute_uri(photo.image.url),
                "taken_at": photo.taken_at,
            },
            status=201,
        )


class StartTripView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=StartTripSerializer, responses={200: BookingSerializer})
    def post(self, request, pk):
        serializer = StartTripSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            start_trip(
                booking_id=pk,
                user=request.user,
                qr_code=data["qr_code"],
                latitude=data["latitude"],
                longitude=data["longitude"],
                fuel_percent=data.get("fuel_percent"),
            )
        except BookingError as exc:
            return error_response(exc)

        return booking_response(request, pk)


class ExtendTripView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=ExtendSerializer, responses={200: BookingSerializer})
    def post(self, request, pk):
        serializer = ExtendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            extend_trip(
                booking_id=pk,
                user=request.user,
                hours=serializer.validated_data["hours"],
                idempotency_key=get_idempotency_key(request),
            )
        except BookingError as exc:
            return error_response(exc)

        return booking_response(request, pk)


class EndTripView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=EndTripSerializer, responses={200: BookingSerializer})
    def post(self, request, pk):
        serializer = EndTripSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            end_trip(
                booking_id=pk,
                user=request.user,
                latitude=data["latitude"],
                longitude=data["longitude"],
                fuel_percent=data.get("fuel_percent"),
            )
        except BookingError as exc:
            return error_response(exc)

        return booking_response(request, pk)


class DamageReportView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=DamageCreateSerializer, responses={201: BookingSerializer})
    def post(self, request, pk):
        serializer = DamageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            create_damage_report(
                booking_id=pk,
                user=request.user,
                description=data["description"],
                claimed_amount=data["claimed_amount"],
            )
        except BookingError as exc:
            return error_response(exc)

        return booking_response(request, pk, status=201)


class DamageRespondView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=DamageRespondSerializer, responses={200: BookingSerializer})
    def post(self, request, pk):
        serializer = DamageRespondSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            respond_damage(
                booking_id=pk,
                user=request.user,
                note=serializer.validated_data["note"],
            )
        except BookingError as exc:
            return error_response(exc)

        return booking_response(request, pk)


class MyVehicleQrView(APIView):
    """The signed code the owner prints and sticks on the vehicle."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: None})
    def get(self, request, pk):
        vehicle = get_object_or_404(Vehicle, pk=pk, owner=request.user)
        return Response({"qr_code": qr_code_for_vehicle(vehicle.pk)})


class DevQrView(APIView):
    """Development only: lets the demo skip scanning a real QR sticker."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: None})
    def get(self, request, pk):
        if not settings.DEBUG:
            raise Http404()
        booking = get_object_or_404(Booking, pk=pk, renter=request.user)
        return Response({"qr_code": qr_code_for_vehicle(booking.vehicle_id)})
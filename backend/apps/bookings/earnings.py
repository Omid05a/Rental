from django.db.models import Q, Sum
from django.urls import path
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Booking


def compute_earnings(owner, limit=100):
    """Income of an owner from finished trips and from fees of late cancellations
    made by renters. Every amount is whole Toman."""
    earning_bookings = (
        Booking.objects.filter(vehicle__owner=owner)
        .filter(
            Q(status=Booking.Status.COMPLETED)
            | Q(
                status=Booking.Status.CANCELLED,
                cancelled_by="renter",
                cancellation_fee__gt=0,
            )
        )
        .select_related("vehicle")
    )

    items = []
    for booking in earning_bookings:
        if booking.status == Booking.Status.COMPLETED:
            kind = "trip"
            date = booking.ended_at
            gross = (
                booking.rental_amount
                + booking.late_fee
                + booking.fuel_fee
                + booking.damage_deduction
            )
        else:
            kind = "cancellation"
            date = booking.cancelled_at
            gross = booking.cancellation_fee

        items.append(
            {
                "booking_id": booking.pk,
                "vehicle_id": booking.vehicle_id,
                "vehicle_title": booking.vehicle.title,
                "kind": kind,
                "date": date,
                "gross": gross,
                "fee": booking.platform_fee,
                "net": gross - booking.platform_fee,
            }
        )
    items.sort(key=lambda item: item["date"], reverse=True)

    by_vehicle = {}
    for item in items:
        row = by_vehicle.setdefault(
            item["vehicle_id"],
            {
                "vehicle_id": item["vehicle_id"],
                "title": item["vehicle_title"],
                "trips": 0,
                "net": 0,
            },
        )
        row["net"] += item["net"]
        if item["kind"] == "trip":
            row["trips"] += 1

    pending = Booking.objects.filter(
        vehicle__owner=owner,
        status__in=[Booking.Status.CONFIRMED, Booking.Status.ACTIVE],
    ).aggregate(total=Sum("rental_amount"))["total"]

    return {
        "total_gross": sum(item["gross"] for item in items),
        "total_fees": sum(item["fee"] for item in items),
        "total_net": sum(item["net"] for item in items),
        "trips": sum(1 for item in items if item["kind"] == "trip"),
        "cancellations": sum(1 for item in items if item["kind"] == "cancellation"),
        "pending_gross": pending or 0,
        "by_vehicle": sorted(by_vehicle.values(), key=lambda row: -row["net"]),
        "items": items[:limit],
    }


class EarningsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: None})
    def get(self, request):
        return Response(compute_earnings(request.user))


urlpatterns = [
    path("earnings/", EarningsView.as_view(), name="earnings"),
]
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import MAX_PHOTOS, Vehicle, VehiclePhoto
from .permissions import IsVerifiedUser
from .serializers import (
    PhotoUploadSerializer,
    VehicleListSerializer,
    VehiclePhotoSerializer,
    VehicleSerializer,
)


class VehiclePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 50


def public_vehicles():
    return (
        Vehicle.objects.filter(
            approval_status=Vehicle.ApprovalStatus.APPROVED, is_active=True
        )
        .select_related("owner")
        .prefetch_related("photos")
    )


def read_number(params, name, errors, cast=float):
    raw = params.get(name)
    if raw in (None, ""):
        return None
    try:
        return cast(raw)
    except (TypeError, ValueError):
        errors[name] = "Enter a valid number."
        return None


class VehicleListView(generics.ListAPIView):
    """Public search. Query: kind, min_price, max_price, lat, lng, radius_km, ordering."""

    serializer_class = VehicleListSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    pagination_class = VehiclePagination

    def get_queryset(self):
        params = self.request.query_params
        errors = {}
        queryset = public_vehicles()

        kind = params.get("kind")
        if kind:
            if kind in Vehicle.Kind.values:
                queryset = queryset.filter(kind=kind)
            else:
                errors["kind"] = "Unknown vehicle type."

        min_price = read_number(params, "min_price", errors, int)
        max_price = read_number(params, "max_price", errors, int)
        if min_price is not None:
            queryset = queryset.filter(price_per_hour__gte=min_price)
        if max_price is not None:
            queryset = queryset.filter(price_per_hour__lte=max_price)

        lat = read_number(params, "lat", errors)
        lng = read_number(params, "lng", errors)
        radius = read_number(params, "radius_km", errors)
        point = None
        if (lat is None) != (lng is None):
            errors["lat"] = "Send lat and lng together."
        elif lat is not None:
            if not -90 <= lat <= 90:
                errors["lat"] = "Latitude must be between -90 and 90."
            elif not -180 <= lng <= 180:
                errors["lng"] = "Longitude must be between -180 and 180."
            else:
                point = Point(lng, lat, srid=4326)
                radius_km = min(max(radius if radius is not None else 10.0, 0.1), 100.0)
                queryset = queryset.filter(
                    location__dwithin=(point, D(km=radius_km))
                ).annotate(distance=Distance("location", point))

        if errors:
            raise ValidationError(errors)

        ordering = params.get("ordering")
        if ordering == "price":
            return queryset.order_by("price_per_hour", "id")
        if ordering == "-price":
            return queryset.order_by("-price_per_hour", "id")
        if point is not None and ordering != "newest":
            return queryset.order_by("distance", "id")
        return queryset.order_by("-created_at", "id")


class VehicleDetailView(generics.RetrieveAPIView):
    serializer_class = VehicleSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def get_queryset(self):
        return public_vehicles()


class MyVehicleListCreateView(generics.ListCreateAPIView):
    serializer_class = VehicleSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsVerifiedUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return Vehicle.objects.filter(owner=self.request.user).prefetch_related(
            "photos"
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class MyVehicleDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = VehicleSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        return Vehicle.objects.filter(owner=self.request.user).prefetch_related(
            "photos"
        )


class VehiclePhotoCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    @extend_schema(
        request=PhotoUploadSerializer, responses={201: VehiclePhotoSerializer}
    )
    def post(self, request, pk):
        vehicle = get_object_or_404(Vehicle, pk=pk, owner=request.user)
        count = vehicle.photos.count()
        if count >= MAX_PHOTOS:
            return Response(
                {
                    "detail": f"At most {MAX_PHOTOS} photos are allowed.",
                    "code": "too_many_photos",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PhotoUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        photo = VehiclePhoto.objects.create(
            vehicle=vehicle,
            image=serializer.validated_data["image"],
            position=count,
        )
        data = VehiclePhotoSerializer(photo, context={"request": request}).data
        return Response(data, status=status.HTTP_201_CREATED)


class VehiclePhotoDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={204: None})
    def delete(self, request, pk, photo_id):
        photo = get_object_or_404(
            VehiclePhoto, pk=photo_id, vehicle__pk=pk, vehicle__owner=request.user
        )
        photo.image.delete(save=False)
        photo.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
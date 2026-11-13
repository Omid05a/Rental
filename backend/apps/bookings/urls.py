from django.urls import path

from .views import (
    BookingCancelView,
    BookingDetailView,
    BookingListCreateView,
    BusyView,
    DamageReportView,
    DamageRespondView,
    DevQrView,
    EndTripView,
    ExtendTripView,
    MyVehicleQrView,
    QuoteView,
    StartTripView,
    TermsView,
    TripPhotoView,
)

urlpatterns = [
    path("terms/", TermsView.as_view(), name="terms"),
    path("vehicles/<int:pk>/busy/", BusyView.as_view(), name="vehicle-busy"),
    path("my/vehicles/<int:pk>/qr/", MyVehicleQrView.as_view(), name="vehicle-qr"),
    path("bookings/quote/", QuoteView.as_view(), name="booking-quote"),
    path("bookings/", BookingListCreateView.as_view(), name="booking-list"),
    path("bookings/<int:pk>/", BookingDetailView.as_view(), name="booking-detail"),
    path(
        "bookings/<int:pk>/cancel/",
        BookingCancelView.as_view(),
        name="booking-cancel",
    ),
    path("bookings/<int:pk>/photos/", TripPhotoView.as_view(), name="trip-photo"),
    path("bookings/<int:pk>/start/", StartTripView.as_view(), name="trip-start"),
    path("bookings/<int:pk>/extend/", ExtendTripView.as_view(), name="trip-extend"),
    path("bookings/<int:pk>/end/", EndTripView.as_view(), name="trip-end"),
    path("bookings/<int:pk>/damage/", DamageReportView.as_view(), name="damage-create"),
    path(
        "bookings/<int:pk>/damage/respond/",
        DamageRespondView.as_view(),
        name="damage-respond",
    ),
    path("bookings/<int:pk>/dev-qr/", DevQrView.as_view(), name="dev-qr"),
]
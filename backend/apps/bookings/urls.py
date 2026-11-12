from django.urls import path

from .views import (
    BookingCancelView,
    BookingDetailView,
    BookingListCreateView,
    BusyView,
    QuoteView,
    TermsView,
)

urlpatterns = [
    path("terms/", TermsView.as_view(), name="terms"),
    path("vehicles/<int:pk>/busy/", BusyView.as_view(), name="vehicle-busy"),
    path("bookings/quote/", QuoteView.as_view(), name="booking-quote"),
    path("bookings/", BookingListCreateView.as_view(), name="booking-list"),
    path("bookings/<int:pk>/", BookingDetailView.as_view(), name="booking-detail"),
    path(
        "bookings/<int:pk>/cancel/",
        BookingCancelView.as_view(),
        name="booking-cancel",
    ),
]
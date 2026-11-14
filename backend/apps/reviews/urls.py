from django.urls import path

from .views import BookingReviewView, VehicleRatingsView, VehicleReviewsView

urlpatterns = [
    path("bookings/<int:pk>/review/", BookingReviewView.as_view(), name="booking-review"),
    path("vehicles/<int:pk>/reviews/", VehicleReviewsView.as_view(), name="vehicle-reviews"),
    path("reviews/vehicles/", VehicleRatingsView.as_view(), name="vehicle-ratings"),
]
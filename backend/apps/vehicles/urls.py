from django.urls import path

from .views import (
    MyVehicleDetailView,
    MyVehicleListCreateView,
    VehicleDetailView,
    VehicleListView,
    VehiclePhotoCreateView,
    VehiclePhotoDeleteView,
)

urlpatterns = [
    path("vehicles/", VehicleListView.as_view(), name="vehicle-list"),
    path("vehicles/<int:pk>/", VehicleDetailView.as_view(), name="vehicle-detail"),
    path("my/vehicles/", MyVehicleListCreateView.as_view(), name="my-vehicle-list"),
    path(
        "my/vehicles/<int:pk>/",
        MyVehicleDetailView.as_view(),
        name="my-vehicle-detail",
    ),
    path(
        "my/vehicles/<int:pk>/photos/",
        VehiclePhotoCreateView.as_view(),
        name="vehicle-photo-create",
    ),
    path(
        "my/vehicles/<int:pk>/photos/<int:photo_id>/",
        VehiclePhotoDeleteView.as_view(),
        name="vehicle-photo-delete",
    ),
]
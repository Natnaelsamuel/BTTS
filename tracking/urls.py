from django.urls import path

from . import views

urlpatterns = [
    path(
        "trips/<uuid:trip_id>/location/",
        views.DriverTripLocationUpdateAPIView.as_view(),
        name="driver_trip_location_update",
    ),
    path(
        "trips/<uuid:trip_id>/current-location/",
        views.TripCurrentLocationAPIView.as_view(),
        name="trip_current_location",
    ),
]

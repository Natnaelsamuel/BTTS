from rest_framework import status
from rest_framework.response import Response

from trips.models import Trip, TripStatus

from .models import Location
from .serializers import LocationSerializer, LocationUpdateSerializer


def create_trip_location(trip: Trip, latitude, longitude) -> Response:
    if trip.status != TripStatus.IN_PROGRESS:
        return Response(
            {"detail": "Location updates are only allowed while the trip is in progress."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = LocationUpdateSerializer(
        data={"latitude": latitude, "longitude": longitude}
    )
    serializer.is_valid(raise_exception=True)

    location = Location.objects.create(
        trip=trip,
        latitude=serializer.validated_data["latitude"],
        longitude=serializer.validated_data["longitude"],
    )
    return Response(LocationSerializer(location).data, status=status.HTTP_201_CREATED)

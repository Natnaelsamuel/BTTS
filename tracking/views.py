# pylint: disable=no-member

from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from trips.models import Trip
from users.permissions import IsDriverRole

from .models import Location
from .serializers import LocationSerializer, LocationUpdateSerializer


class DriverTripLocationUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated, IsDriverRole]

    def post(self, request, trip_id):
        trip = Trip.objects.filter(pk=trip_id).first()
        if trip is None:
            raise NotFound("Trip not found.")

        if trip.driver_id != request.user.id:
            raise PermissionDenied("You are not assigned to this trip.")

        serializer = LocationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        location = Location.objects.create(
            trip=trip,
            latitude=serializer.validated_data["latitude"],
            longitude=serializer.validated_data["longitude"],
        )
        return Response(LocationSerializer(location).data, status=status.HTTP_201_CREATED)


class TripCurrentLocationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, trip_id):
        _ = request
        if not Trip.objects.filter(pk=trip_id).exists():
            raise NotFound("Trip not found.")

        location = Location.objects.filter(trip_id=trip_id).order_by("-timestamp").first()
        if location is None:
            raise NotFound("No location found for this trip.")

        return Response(LocationSerializer(location).data, status=status.HTTP_200_OK)

# pylint: disable=no-member

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.permissions import IsAdminRole, IsDriverRole, IsPassengerRole

from .models import Trip
from .serializers import TripAssignDriverSerializer, TripSerializer, TripStatusUpdateSerializer


class AdminTripViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Trip.objects.select_related("bus", "route", "driver").all()
    serializer_class = TripSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]

    @action(detail=True, methods=["patch"], url_path="assign-driver")
    def assign_driver(self, request, pk=None):
        _ = pk
        trip = self.get_object()
        serializer = TripAssignDriverSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        driver_id = serializer.validated_data["driver_id"]
        trip.driver_id = driver_id
        trip.save(update_fields=["driver", "updated_at"])
        return Response(TripSerializer(trip).data)


class PassengerTripViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = TripSerializer
    permission_classes = [IsAuthenticated, IsPassengerRole]

    def get_queryset(self):
        queryset = Trip.objects.select_related("bus", "route", "driver").all()

        origin = self.request.query_params.get("origin")
        destination = self.request.query_params.get("destination")
        departure_date = self.request.query_params.get("departure_date")

        if origin:
            queryset = queryset.filter(route__origin__icontains=origin)
        if destination:
            queryset = queryset.filter(
                route__destination__icontains=destination)
        if departure_date:
            queryset = queryset.filter(departure_time__date=departure_date)

        return queryset


class DriverAssignedTripViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = TripSerializer
    permission_classes = [IsAuthenticated, IsDriverRole]

    def get_queryset(self):
        return Trip.objects.select_related("bus", "route", "driver").filter(driver=self.request.user)

    @action(detail=True, methods=["patch"], url_path="status")
    def update_status(self, request, pk=None):
        _ = pk
        trip = self.get_object()
        serializer = TripStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        trip.status = serializer.validated_data["status"]
        trip.save(update_fields=["status", "updated_at"])
        return Response(TripSerializer(trip).data, status=status.HTTP_200_OK)

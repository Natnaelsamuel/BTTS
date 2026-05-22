# pylint: disable=no-member

from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from tickets.models import Ticket, TicketStatus
from tickets.ticket_lifecycle import sync_tickets_for_trip
from users.permissions import IsAdminRole, IsDriverRole, IsPassengerRole

from .models import Trip, TripStatus
from .serializers import (
    TripAssignDriverSerializer,
    TripCancelSerializer,
    TripSerializer,
    TripStatusUpdateSerializer,
)


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

    def perform_update(self, serializer):
        instance = serializer.instance
        previous_status = instance.status
        trip = serializer.save()
        if trip.status != previous_status:
            sync_tickets_for_trip(trip)

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

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel_trip(self, request, pk=None):
        _ = pk
        trip = self.get_object()
        if trip.status == TripStatus.CANCELLED:
            return Response(
                {"detail": "Trip is already cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if trip.status == TripStatus.COMPLETED:
            return Response(
                {"detail": "Completed trips cannot be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = TripCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        trip.status = TripStatus.CANCELLED
        trip.save(update_fields=["status", "updated_at"])
        sync_tickets_for_trip(trip)
        return Response(TripSerializer(trip).data, status=status.HTTP_200_OK)


class PassengerTripViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = TripSerializer

    def get_permissions(self):
        # Public pages can browse trips without authentication.
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]

        # Seat availability is needed during booking for any signed-in user.
        if self.action == "booked_seats":
            return [IsAuthenticated()]

        return [IsAuthenticated(), IsPassengerRole()]

    def get_queryset(self):
        queryset = Trip.objects.select_related("bus", "route", "driver").filter(
            departure_time__date__gte=timezone.localdate()
        )

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

    @action(detail=True, methods=["get"], url_path="booked-seats")
    def booked_seats(self, request, pk=None):
        """Get list of booked/reserved seat numbers for a trip."""
        _ = request, pk
        trip = self.get_object()
        booked = Ticket.objects.filter(
            trip=trip,
            status__in=[TicketStatus.BOOKED, TicketStatus.RESERVED]
        ).values_list("seat__seat_number", flat=True)

        return Response({
            "trip_id": str(trip.id),
            "booked_seats": list(booked)
        }, status=status.HTTP_200_OK)


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
        sync_tickets_for_trip(trip)
        return Response(TripSerializer(trip).data, status=status.HTTP_200_OK)

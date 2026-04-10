# pylint: disable=no-member

from django.db.models import Exists, OuterRef
from rest_framework import generics, viewsets
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated

from tickets.models import Ticket, TicketStatus
from trips.models import Trip
from users.permissions import IsAdminRole

from .models import Bus, Seat
from .serializers import BusSerializer, SeatSerializer


class AdminBusViewSet(viewsets.ModelViewSet):
    queryset = Bus.objects.all()
    serializer_class = BusSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]


class BusSeatListAPIView(generics.ListAPIView):
    serializer_class = SeatSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        bus_or_trip_id = self.kwargs.get("bus_id")

        bus = Bus.objects.filter(pk=bus_or_trip_id).first()

        trip_id = (
            self.request.query_params.get("trip_id")
            or self.request.query_params.get("trip")
            or self.request.query_params.get("tripId")
        )

        # Support accidental trip-id-in-path usage by resolving the trip and its bus.
        if bus is None:
            path_trip = Trip.objects.select_related(
                "bus").filter(pk=bus_or_trip_id).first()
            if path_trip is None:
                raise NotFound("Bus not found.")
            bus = path_trip.bus
            if not trip_id:
                trip_id = str(path_trip.id)

        queryset = Seat.objects.filter(bus_id=bus.id).order_by("seat_number")

        if not trip_id:
            # Without trip context, mark unavailable if seat has any active booking on this bus.
            booked_ticket_exists = Ticket.objects.filter(
                trip__bus_id=bus.id,
                seat_id=OuterRef("pk"),
                status=TicketStatus.BOOKED,
            )
            return queryset.annotate(is_available=~Exists(booked_ticket_exists))

        trip = Trip.objects.filter(pk=trip_id, bus_id=bus.id).first()
        if trip is None:
            raise NotFound("Trip not found for this bus.")

        booked_ticket_exists = Ticket.objects.filter(
            trip_id=trip_id,
            seat_id=OuterRef("pk"),
            status=TicketStatus.BOOKED,
        )

        return queryset.annotate(is_available=~Exists(booked_ticket_exists))

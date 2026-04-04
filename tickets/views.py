# pylint: disable=no-member

from django.db import IntegrityError, transaction
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.permissions import IsPassengerRole

from .models import Ticket, TicketStatus
from .serializers import TicketBookingSerializer, TicketCancelSerializer, TicketSerializer


class PassengerTicketViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated, IsPassengerRole]

    def get_serializer_class(self):
        if self.action == "create":
            return TicketBookingSerializer
        if self.action == "cancel_ticket":
            return TicketCancelSerializer
        return TicketSerializer

    def get_queryset(self):
        return Ticket.objects.select_related("trip", "seat", "user").filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        _ = args, kwargs
        booking_serializer = TicketBookingSerializer(data=request.data)
        booking_serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                ticket = Ticket.objects.create(
                    user=request.user,
                    trip=booking_serializer.validated_data["trip"],
                    seat=booking_serializer.validated_data["seat"],
                    status=TicketStatus.BOOKED,
                )
        except IntegrityError:
            return Response(
                {"detail": "This seat is already booked for the selected trip."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(TicketSerializer(ticket).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch"], url_path="cancel")
    def cancel_ticket(self, request, pk=None):
        _ = pk
        ticket = self.get_object()
        if ticket.status == TicketStatus.CANCELLED:
            return Response({"detail": "Ticket is already cancelled."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = TicketCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ticket.status = TicketStatus.CANCELLED
        ticket.save(update_fields=["status", "updated_at"])
        return Response(TicketSerializer(ticket).data, status=status.HTTP_200_OK)

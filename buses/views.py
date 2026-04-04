# pylint: disable=no-member

from rest_framework import generics, viewsets
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated

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
        bus_id = self.kwargs.get("bus_id")
        if not Bus.objects.filter(pk=bus_id).exists():
            raise NotFound("Bus not found.")
        return Seat.objects.filter(bus_id=bus_id).order_by("seat_number")

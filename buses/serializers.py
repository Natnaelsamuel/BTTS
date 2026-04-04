from rest_framework import serializers

from .models import Bus, Seat


class BusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bus
        fields = ["id", "plate_number", "capacity", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class SeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seat
        fields = ["id", "bus", "seat_number"]
        read_only_fields = ["id"]

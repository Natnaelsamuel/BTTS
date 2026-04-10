from rest_framework import serializers

from .models import Bus, Seat


class BusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bus
        fields = ["id", "plate_number", "capacity", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class SeatSerializer(serializers.ModelSerializer):
    is_available = serializers.BooleanField(read_only=True, default=True)

    class Meta:
        model = Seat
        fields = ["id", "bus", "seat_number", "is_available"]
        read_only_fields = ["id"]

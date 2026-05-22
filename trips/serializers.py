# pyright: reportAttributeAccessIssue=false

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Trip, TripStatus

User = get_user_model()


class TripSerializer(serializers.ModelSerializer):
    bus_plate_number = serializers.CharField(
        source="bus.plate_number", read_only=True)
    route_label = serializers.SerializerMethodField()
    driver_username = serializers.CharField(
        source="driver.username", read_only=True)
    bus_detail = serializers.SerializerMethodField()
    route_detail = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = [
            "id",
            "bus",
            "bus_plate_number",
            "bus_detail",
            "route",
            "route_label",
            "route_detail",
            "departure_time",
            "arrival_time",
            "fare",
            "driver",
            "driver_username",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at",
                            "bus_plate_number", "route_label", "driver_username"]

    def get_route_label(self, obj):
        return f"{obj.route.origin} -> {obj.route.destination}"

    def get_bus_detail(self, obj):
        return {
            "id": str(obj.bus_id),
            "plate_number": obj.bus.plate_number,
            "capacity": obj.bus.capacity,
        }

    def get_route_detail(self, obj):
        return {
            "id": str(obj.route_id),
            "origin": obj.route.origin,
            "destination": obj.route.destination,
        }

    def validate_driver(self, value):
        if value.role != "DRIVER":
            raise serializers.ValidationError(
                "Assigned user must have DRIVER role.")
        return value


class TripAssignDriverSerializer(serializers.Serializer):
    driver_id = serializers.UUIDField()

    def validate_driver_id(self, value):
        try:
            user = User.objects.get(pk=value)
        except User.DoesNotExist as exc:
            raise serializers.ValidationError("Driver not found.") from exc

        if user.role != "DRIVER":
            raise serializers.ValidationError("Selected user is not a driver.")
        return value

    def create(self, validated_data):
        raise NotImplementedError("TripAssignDriverSerializer is input-only.")

    def update(self, instance, validated_data):
        raise NotImplementedError("TripAssignDriverSerializer is input-only.")


class TripStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=TripStatus.choices)

    def create(self, validated_data):
        raise NotImplementedError("TripStatusUpdateSerializer is input-only.")

    def update(self, instance, validated_data):
        raise NotImplementedError("TripStatusUpdateSerializer is input-only.")


class TripCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def create(self, validated_data):
        raise NotImplementedError("TripCancelSerializer is input-only.")

    def update(self, instance, validated_data):
        raise NotImplementedError("TripCancelSerializer is input-only.")

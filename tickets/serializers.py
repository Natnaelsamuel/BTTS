# pyright: reportAttributeAccessIssue=false
# pylint: disable=no-member

from rest_framework import serializers

from buses.models import Seat
from trips.models import Trip, TripStatus

from .models import Payment, Ticket


class TicketSerializer(serializers.ModelSerializer):
    trip_status = serializers.CharField(source="trip.status", read_only=True)

    class Meta:
        model = Ticket
        fields = ["id", "user", "trip", "seat", "fare_amount", "status",
                  "trip_status", "booked_at", "updated_at"]
        read_only_fields = ["id", "user",
                    "trip_status", "fare_amount", "booked_at", "updated_at"]


class TicketBookingSerializer(serializers.Serializer):
    trip_id = serializers.UUIDField()
    seat_id = serializers.IntegerField()

    def validate(self, attrs):
        trip = Trip.objects.filter(pk=attrs["trip_id"]).first()
        if trip is None:
            raise serializers.ValidationError({"trip_id": "Trip not found."})

        seat = Seat.objects.filter(pk=attrs["seat_id"]).first()
        if seat is None:
            raise serializers.ValidationError({"seat_id": "Seat not found."})

        if seat.bus_id != trip.bus_id:
            raise serializers.ValidationError(
                {"seat_id": "Seat does not belong to the selected trip bus."})

        if trip.status != TripStatus.SCHEDULED:
            raise serializers.ValidationError(
                {"trip_id": "Only scheduled trips can be booked."})

        attrs["trip"] = trip
        attrs["seat"] = seat
        return attrs

    def create(self, validated_data):
        raise NotImplementedError("TicketBookingSerializer is input-only.")

    def update(self, instance, validated_data):
        raise NotImplementedError("TicketBookingSerializer is input-only.")


class TicketCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        return attrs

    def create(self, validated_data):
        raise NotImplementedError("TicketCancelSerializer is input-only.")

    def update(self, instance, validated_data):
        raise NotImplementedError("TicketCancelSerializer is input-only.")


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "ticket",
            "amount",
            "currency",
            "provider",
            "status",
            "tx_ref",
            "checkout_url",
            "paid_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class PaymentInitSerializer(serializers.Serializer):
    return_url = serializers.URLField(required=False)

    def create(self, validated_data):
        raise NotImplementedError("PaymentInitSerializer is input-only.")

    def update(self, instance, validated_data):
        raise NotImplementedError("PaymentInitSerializer is input-only.")

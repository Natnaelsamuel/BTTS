# pyright: reportAttributeAccessIssue=false
# pylint: disable=no-member

from rest_framework import serializers

from buses.models import Seat
from trips.models import Trip, TripStatus

from .models import Payment, Ticket
from .ticket_lifecycle import can_download_ticket, is_ticket_expired


class TicketSerializer(serializers.ModelSerializer):
    trip_status = serializers.CharField(source="trip.status", read_only=True)
    seat_number = serializers.CharField(
        source="seat.seat_number", read_only=True)
    trip_detail = serializers.SerializerMethodField()
    passenger_name = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    can_download = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            "id",
            "user",
            "trip",
            "seat",
            "seat_number",
            "trip_detail",
            "passenger_name",
            "fare_amount",
            "status",
            "trip_status",
            "payment_status",
            "is_expired",
            "can_download",
            "booked_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_passenger_name(self, obj):
        return obj.user.get_full_name() or obj.user.email or obj.user.username

    def get_payment_status(self, obj):
        payment = getattr(obj, "payment", None)
        if payment is None:
            return None
        return payment.status

    def get_is_expired(self, obj):
        return is_ticket_expired(obj)

    def get_can_download(self, obj):
        return can_download_ticket(obj)

    def get_trip_detail(self, obj):
        return {
            "id": str(obj.trip_id),
            "departure_time": obj.trip.departure_time,
            "arrival_time": obj.trip.arrival_time,
            "status": obj.trip.status,
            "route_detail": {
                "origin": obj.trip.route.origin,
                "destination": obj.trip.route.destination,
            },
            "bus_detail": {
                "plate_number": obj.trip.bus.plate_number,
                "capacity": obj.trip.bus.capacity,
            },
            "driver_name": obj.trip.driver.get_full_name() or obj.trip.driver.username,
        }


class TicketBookingSerializer(serializers.Serializer):
    trip_id = serializers.UUIDField()
    seat_id = serializers.IntegerField()

    def validate(self, attrs):
        trip = Trip.objects.filter(pk=attrs["trip_id"]).first()
        if trip is None:
            raise serializers.ValidationError({"trip_id": "Trip not found."})

        # Lookup seat by bus and seat_number (not by pk)
        seat = Seat.objects.filter(
            bus_id=trip.bus_id,
            seat_number=str(attrs["seat_id"])
        ).first()
        if seat is None:
            raise serializers.ValidationError(
                {"seat_id": f"Seat {attrs['seat_id']} not found on this bus."})

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

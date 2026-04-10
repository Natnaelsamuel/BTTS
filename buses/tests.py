# pylint: disable=no-member

import uuid
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from routes.models import Route
from tickets.models import Ticket, TicketStatus
from trips.models import Trip
from users.models import User, UserRole

from .models import Bus, Seat


class BusSeatListAPITests(APITestCase):
    def setUp(self):
        self.driver = User.objects.create_user(
            username="driver_bus_api",
            email="driver_bus_api@example.com",
            password="strongPass123",
            role=UserRole.DRIVER,
        )
        self.passenger = User.objects.create_user(
            username="passenger_bus_api",
            email="passenger_bus_api@example.com",
            password="strongPass123",
            role=UserRole.PASSENGER,
        )
        self.bus = Bus.objects.create(plate_number="KHH-888H", capacity=4)
        self.route = Route.objects.create(
            origin="Nairobi", destination="Kisumu", distance=Decimal("350.00")
        )
        departure = timezone.now() + timedelta(hours=2)
        arrival = departure + timedelta(hours=6)
        self.trip = Trip.objects.create(
            bus=self.bus,
            route=self.route,
            departure_time=departure,
            arrival_time=arrival,
            driver=self.driver,
        )

    def test_authenticated_user_can_list_bus_seats(self):
        self.client.force_authenticate(user=self.passenger)

        response = self.client.get(
            f"/api/buses/{self.bus.id}/seats/?trip_id={self.trip.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)
        self.assertTrue(all(seat["is_available"] for seat in response.data))

    def test_can_list_bus_seats_without_trip_id(self):
        self.client.force_authenticate(user=self.passenger)
        response = self.client.get(f"/api/buses/{self.bus.id}/seats/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)

    def test_trip_seat_availability_shows_unavailable_after_booking(self):
        seat_1 = Seat.objects.get(bus=self.bus, seat_number="1")
        Ticket.objects.create(
            user=self.passenger,
            trip=self.trip,
            seat=seat_1,
            status=TicketStatus.BOOKED,
        )

        self.client.force_authenticate(user=self.passenger)
        response = self.client.get(
            f"/api/buses/{self.bus.id}/seats/?trip_id={self.trip.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)
        seat_map = {seat["seat_number"]: seat["is_available"]
                    for seat in response.data}
        self.assertFalse(seat_map["1"])
        self.assertTrue(seat_map["2"])

    def test_trip_id_must_match_bus(self):
        other_bus = Bus.objects.create(plate_number="KOO-123O", capacity=2)
        other_route = Route.objects.create(
            origin="Eldoret", destination="Nakuru", distance=Decimal("120.00")
        )
        departure = timezone.now() + timedelta(hours=1)
        arrival = departure + timedelta(hours=3)
        other_trip = Trip.objects.create(
            bus=other_bus,
            route=other_route,
            departure_time=departure,
            arrival_time=arrival,
            driver=self.driver,
        )

        self.client.force_authenticate(user=self.passenger)
        response = self.client.get(
            f"/api/buses/{self.bus.id}/seats/?trip_id={other_trip.id}")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_trip_query_alias_is_supported(self):
        self.client.force_authenticate(user=self.passenger)
        response = self.client.get(
            f"/api/buses/{self.bus.id}/seats/?trip={self.trip.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_trip_id_in_path_is_supported(self):
        seat_1 = Seat.objects.get(bus=self.bus, seat_number="1")
        Ticket.objects.create(
            user=self.passenger,
            trip=self.trip,
            seat=seat_1,
            status=TicketStatus.BOOKED,
        )

        self.client.force_authenticate(user=self.passenger)
        response = self.client.get(f"/api/buses/{self.trip.id}/seats/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        seat_map = {seat["seat_number"]: seat["is_available"]
                    for seat in response.data}
        self.assertFalse(seat_map["1"])

    def test_returns_404_for_unknown_bus(self):
        self.client.force_authenticate(user=self.passenger)
        response = self.client.get(f"/api/buses/{uuid.uuid4()}/seats/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_requires_authentication(self):
        response = self.client.get(
            f"/api/buses/{self.bus.id}/seats/?trip_id={self.trip.id}")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_bus_creation_auto_generates_seats(self):
        bus = Bus.objects.create(plate_number="KJJ-999J", capacity=3)
        self.assertEqual(Seat.objects.filter(bus=bus).count(), 3)

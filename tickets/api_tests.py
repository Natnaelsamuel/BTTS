# pylint: disable=no-member
# pyright: reportAttributeAccessIssue=false

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from buses.models import Bus, Seat
from routes.models import Route
from trips.models import Trip
from users.models import User, UserRole

from .models import TicketStatus


class PassengerTicketAPITests(APITestCase):
    def setUp(self):
        self.driver = User.objects.create_user(
            username="driver_ticket",
            email="driver_ticket@example.com",
            password="strongPass123",
            role=UserRole.DRIVER,
        )
        self.passenger = User.objects.create_user(
            username="passenger_ticket",
            email="passenger_ticket@example.com",
            password="strongPass123",
            role=UserRole.PASSENGER,
        )

        self.bus = Bus.objects.create(plate_number="KFF-666F", capacity=40)
        self.seat_1 = Seat.objects.filter(
            bus=self.bus, seat_number="1").first()
        self.route = Route.objects.create(
            origin="Nairobi", destination="Mombasa", distance=Decimal("480.00"))

        departure = timezone.now() + timedelta(hours=3)
        arrival = departure + timedelta(hours=8)
        self.trip = Trip.objects.create(
            bus=self.bus,
            route=self.route,
            departure_time=departure,
            arrival_time=arrival,
            driver=self.driver,
        )

    def test_passenger_can_book_and_cancel_ticket(self):
        self.client.force_authenticate(user=self.passenger)

        book_response = self.client.post(
            "/api/passenger/tickets/",
            {"trip_id": self.trip.id, "seat_id": self.seat_1.id},
            format="json",
        )
        self.assertEqual(book_response.status_code, status.HTTP_201_CREATED)

        ticket_id = book_response.data["id"]
        cancel_response = self.client.patch(
            f"/api/passenger/tickets/{ticket_id}/cancel/", {}, format="json")
        self.assertEqual(cancel_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            cancel_response.data["status"], TicketStatus.CANCELLED)

    def test_booking_same_seat_twice_returns_error(self):
        self.client.force_authenticate(user=self.passenger)
        first = self.client.post(
            "/api/passenger/tickets/",
            {"trip_id": self.trip.id, "seat_id": self.seat_1.id},
            format="json",
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)

        second = self.client.post(
            "/api/passenger/tickets/",
            {"trip_id": self.trip.id, "seat_id": self.seat_1.id},
            format="json",
        )
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)

    def test_passenger_cannot_book_seat_from_other_bus(self):
        other_bus = Bus.objects.create(plate_number="KGG-777G", capacity=30)
        other_seat = Seat.objects.filter(
            bus=other_bus, seat_number="1").first()

        self.client.force_authenticate(user=self.passenger)
        response = self.client.post(
            "/api/passenger/tickets/",
            {"trip_id": self.trip.id, "seat_id": other_seat.id},
            format="json",
        )
       
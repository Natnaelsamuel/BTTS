# pylint: disable=no-member

from rest_framework import status
from rest_framework.test import APITestCase

from users.models import User, UserRole

from .models import Bus, Seat


class BusSeatListAPITests(APITestCase):
    def setUp(self):
        self.passenger = User.objects.create_user(
            username="passenger_bus_api",
            email="passenger_bus_api@example.com",
            password="strongPass123",
            role=UserRole.PASSENGER,
        )
        self.bus = Bus.objects.create(plate_number="KHH-888H", capacity=4)

    def test_authenticated_user_can_list_bus_seats(self):
        self.client.force_authenticate(user=self.passenger)

        response = self.client.get(f"/api/buses/{self.bus.id}/seats/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)

    def test_returns_404_for_unknown_bus(self):
        self.client.force_authenticate(user=self.passenger)
        response = self.client.get("/api/buses/99999/seats/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_requires_authentication(self):
        response = self.client.get(f"/api/buses/{self.bus.id}/seats/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_bus_creation_auto_generates_seats(self):
        bus = Bus.objects.create(plate_number="KJJ-999J", capacity=3)
        self.assertEqual(Seat.objects.filter(bus=bus).count(), 3)

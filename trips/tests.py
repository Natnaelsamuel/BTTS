# pylint: disable=no-member

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from buses.models import Bus
from routes.models import Route
from users.models import User, UserRole

from .models import Trip, TripStatus


class CoreTripAPITests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_step4",
            email="admin_step4@example.com",
            password="strongPass123",
            role=UserRole.ADMIN,
        )
        self.driver = User.objects.create_user(
            username="driver_step4",
            email="driver_step4@example.com",
            password="strongPass123",
            role=UserRole.DRIVER,
        )
        self.passenger = User.objects.create_user(
            username="passenger_step4",
            email="passenger_step4@example.com",
            password="strongPass123",
            role=UserRole.PASSENGER,
        )

        self.bus = Bus.objects.create(plate_number="KCC-333C", capacity=40)
        self.route = Route.objects.create(
            origin="Nairobi", destination="Kisumu", distance=Decimal("350.00"))

        departure = timezone.now() + timedelta(hours=2)
        arrival = departure + timedelta(hours=6)
        self.trip = Trip.objects.create(
            bus=self.bus,
            route=self.route,
            departure_time=departure,
            arrival_time=arrival,
            driver=self.driver,
        )

    def test_admin_can_manage_buses_routes_and_trips(self):
        self.client.force_authenticate(user=self.admin)

        bus_response = self.client.post(
            "/api/admin/buses/",
            {"plate_number": "KDD-444D", "capacity": 45},
            format="json",
        )
        self.assertEqual(bus_response.status_code, status.HTTP_201_CREATED)

        route_response = self.client.post(
            "/api/admin/routes/",
            {"origin": "Nakuru", "destination": "Eldoret", "distance": "150.50"},
            format="json",
        )
        self.assertEqual(route_response.status_code, status.HTTP_201_CREATED)

        trip_response = self.client.post(
            "/api/admin/trips/",
            {
                "bus": self.bus.id,
                "route": self.route.id,
                "driver": self.driver.id,
                "departure_time": (timezone.now() + timedelta(days=1)).isoformat(),
                "arrival_time": (timezone.now() + timedelta(days=1, hours=6)).isoformat(),
                "status": TripStatus.SCHEDULED,
            },
            format="json",
        )
        self.assertEqual(trip_response.status_code, status.HTTP_201_CREATED)

    def test_admin_can_assign_driver(self):
        second_driver = User.objects.create_user(
            username="driver_step4_b",
            email="driver_step4_b@example.com",
            password="strongPass123",
            role=UserRole.DRIVER,
        )
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            f"/api/admin/trips/{self.trip.id}/assign-driver/",
            {"driver_id": second_driver.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.driver_id, second_driver.id)

    def test_passenger_can_view_and_search_trips(self):
        self.client.force_authenticate(user=self.passenger)

        list_response = self.client.get("/api/passenger/trips/")
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(list_response.data), 1)

        filtered = self.client.get("/api/passenger/trips/?origin=Nairobi")
        self.assertEqual(filtered.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(filtered.data), 1)

    def test_driver_can_view_assigned_trips_and_update_status(self):
        self.client.force_authenticate(user=self.driver)

        list_response = self.client.get("/api/driver/trips/")
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(list_response.data), 1)

        update_response = self.client.patch(
            f"/api/driver/trips/{self.trip.id}/status/",
            {"status": TripStatus.IN_PROGRESS},
            format="json",
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)

        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, TripStatus.IN_PROGRESS)

    def test_non_admin_cannot_create_bus(self):
        self.client.force_authenticate(user=self.passenger)
        response = self.client.post(
            "/api/admin/buses/",
            {"plate_number": "KEE-555E", "capacity": 50},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_delete_trip(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(f"/api/admin/trips/{self.trip.id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Trip.objects.filter(pk=self.trip.id).exists())

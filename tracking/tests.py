# pylint: disable=no-member

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from buses.models import Bus
from routes.models import Route
from trips.models import Trip, TripStatus
from users.models import User, UserRole

from .models import Location


class TrackingAPITests(APITestCase):
    def setUp(self):
        self.driver = User.objects.create_user(
            username="tracking_driver",
            email="tracking_driver@example.com",
            password="strongPass123",
            role=UserRole.DRIVER,
        )
        self.other_driver = User.objects.create_user(
            username="tracking_other_driver",
            email="tracking_other_driver@example.com",
            password="strongPass123",
            role=UserRole.DRIVER,
        )
        self.passenger = User.objects.create_user(
            username="tracking_passenger",
            email="tracking_passenger@example.com",
            password="strongPass123",
            role=UserRole.PASSENGER,
        )
        self.admin = User.objects.create_user(
            username="tracking_admin",
            email="tracking_admin@example.com",
            password="strongPass123",
            role=UserRole.ADMIN,
        )

        self.bus = Bus.objects.create(plate_number="KTR-101T", capacity=3)
        self.route = Route.objects.create(
            origin="Nairobi", destination="Nakuru", distance=Decimal("160.00")
        )
        departure = timezone.now() + timedelta(hours=1)
        arrival = departure + timedelta(hours=3)
        self.trip = Trip.objects.create(
            bus=self.bus,
            route=self.route,
            departure_time=departure,
            arrival_time=arrival,
            driver=self.driver,
        )

    def test_assigned_driver_can_update_location(self):
        self.trip.status = TripStatus.IN_PROGRESS
        self.trip.save(update_fields=["status"])
        self.client.force_authenticate(user=self.driver)
        response = self.client.post(
            f"/api/tracking/trips/{self.trip.id}/location/",
            {"latitude": "-1.292100", "longitude": "36.821900"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Location.objects.filter(trip=self.trip).count(), 1)

    def test_other_driver_cannot_update_location(self):
        self.client.force_authenticate(user=self.other_driver)
        response = self.client.post(
            f"/api/tracking/trips/{self.trip.id}/location/",
            {"latitude": "-1.292100", "longitude": "36.821900"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_passenger_cannot_update_location(self):
        self.client.force_authenticate(user=self.passenger)
        response = self.client.post(
            f"/api/tracking/trips/{self.trip.id}/location/",
            {"latitude": "-1.292100", "longitude": "36.821900"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_driver_cannot_update_location_when_trip_not_in_progress(self):
        self.client.force_authenticate(user=self.driver)
        response = self.client.post(
            f"/api/tracking/trips/{self.trip.id}/location/",
            {"latitude": "-1.292100", "longitude": "36.821900"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_can_update_location_for_in_progress_trip(self):
        self.trip.status = TripStatus.IN_PROGRESS
        self.trip.save(update_fields=["status"])
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"/api/tracking/admin/trips/{self.trip.id}/location/",
            {"latitude": "-1.280000", "longitude": "36.830000"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Location.objects.filter(trip=self.trip).count(), 1)

    def test_admin_cannot_update_location_when_trip_not_in_progress(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"/api/tracking/admin/trips/{self.trip.id}/location/",
            {"latitude": "-1.280000", "longitude": "36.830000"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_passenger_cannot_use_admin_location_endpoint(self):
        self.trip.status = TripStatus.IN_PROGRESS
        self.trip.save(update_fields=["status"])
        self.client.force_authenticate(user=self.passenger)
        response = self.client.post(
            f"/api/tracking/admin/trips/{self.trip.id}/location/",
            {"latitude": "-1.280000", "longitude": "36.830000"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_current_location_returns_latest_location(self):
        self.trip.status = TripStatus.IN_PROGRESS
        self.trip.save(update_fields=["status"])
        old_location = Location.objects.create(
            trip=self.trip,
            latitude=Decimal("-1.300000"),
            longitude=Decimal("36.800000"),
        )
        Location.objects.filter(pk=old_location.pk).update(
            timestamp=timezone.now() - timedelta(minutes=5)
        )

        self.client.force_authenticate(user=self.admin)
        self.client.post(
            f"/api/tracking/admin/trips/{self.trip.id}/location/",
            {"latitude": "-1.292100", "longitude": "36.821900"},
            format="json",
        )

        response = self.client.get(
            f"/api/tracking/trips/{self.trip.id}/current-location/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["latitude"], "-1.292100")
        self.assertEqual(response.data["longitude"], "36.821900")

    def test_get_current_location_returns_404_when_missing(self):
        self.client.force_authenticate(user=self.passenger)
        response = self.client.get(
            f"/api/tracking/trips/{self.trip.id}/current-location/"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

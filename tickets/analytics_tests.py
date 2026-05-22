# pylint: disable=no-member

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from buses.models import Bus
from routes.models import Route
from trips.models import Trip
from users.models import User, UserRole

from .models import Payment, PaymentStatus, Ticket, TicketStatus


class AdminAnalyticsTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="analytics_admin",
            email="analytics_admin@example.com",
            password="strongPass123",
            role=UserRole.ADMIN,
        )
        self.passenger = User.objects.create_user(
            username="analytics_passenger",
            email="analytics_passenger@example.com",
            password="strongPass123",
            role=UserRole.PASSENGER,
        )
        self.driver = User.objects.create_user(
            username="analytics_driver",
            email="analytics_driver@example.com",
            password="strongPass123",
            role=UserRole.DRIVER,
        )
        self.bus = Bus.objects.create(plate_number="ANA-100A", capacity=20)
        self.route = Route.objects.create(
            origin="Addis Ababa", destination="Hawassa", distance=Decimal("275.00")
        )
        departure = timezone.now() + timedelta(days=2)
        self.trip = Trip.objects.create(
            bus=self.bus,
            route=self.route,
            departure_time=departure,
            arrival_time=departure + timedelta(hours=5),
            fare=Decimal("500.00"),
            driver=self.driver,
        )
        self.seat = self.bus.seats.first()
        self.ticket = Ticket.objects.create(
            user=self.passenger,
            trip=self.trip,
            seat=self.seat,
            fare_amount=Decimal("500.00"),
            status=TicketStatus.BOOKED,
        )
        Payment.objects.create(
            ticket=self.ticket,
            amount=Decimal("500.00"),
            status=PaymentStatus.PAID,
            paid_at=timezone.now(),
        )

    def test_admin_can_fetch_analytics(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/admin/analytics/?days=30")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("summary", response.data)
        self.assertIn("tickets_per_day", response.data)
        self.assertEqual(response.data["summary"]["tickets_sold"], 1)
        self.assertEqual(response.data["summary"]["total_revenue"], "500.00")

    def test_passenger_cannot_fetch_analytics(self):
        self.client.force_authenticate(user=self.passenger)
        response = self.client.get("/api/admin/analytics/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_export_csv(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/admin/analytics/export/?days=30&report=summary")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn("SUMMARY", response.content.decode("utf-8"))
        self.assertIn("attachment", response["Content-Disposition"])

# pylint: disable=no-member,protected-access
# pyright: reportAttributeAccessIssue=false, reportPrivateUsage=false

from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from buses.models import Bus, Seat
from routes.models import Route
from tracking.models import Location
from trips.models import Trip
from users.models import User, UserRole

from .models import Payment, PaymentStatus, Ticket, TicketStatus


class StepTwoModelTests(TestCase):
    def setUp(self):
        self.driver = User.objects.create_user(
            username="driver1",
            password="password123",
            role=UserRole.DRIVER,
        )
        self.passenger = User.objects.create_user(
            username="passenger1",
            password="password123",
            role=UserRole.PASSENGER,
        )

        self.bus = Bus.objects.create(plate_number="KAA-111A", capacity=50)
        self.seat_1 = Seat.objects.create(bus=self.bus, seat_number="1")
        Seat.objects.create(bus=self.bus, seat_number="2")

        self.route = Route.objects.create(
            origin="Nairobi", destination="Mombasa", distance=Decimal("480.50"))

        departure = timezone.now() + timedelta(hours=1)
        arrival = departure + timedelta(hours=8)
        self.trip = Trip.objects.create(
            bus=self.bus,
            route=self.route,
            departure_time=departure,
            arrival_time=arrival,
            driver=self.driver,
        )

    def test_seat_number_must_be_unique_per_bus(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Seat.objects.create(bus=self.bus, seat_number="1")

    def test_trip_arrival_must_be_after_departure(self):
        departure = timezone.now() + timedelta(hours=3)
        arrival = departure - timedelta(minutes=5)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Trip.objects.create(
                    bus=self.bus,
                    route=self.route,
                    departure_time=departure,
                    arrival_time=arrival,
                    driver=self.driver,
                )

    def test_ticket_must_be_unique_for_same_trip_and_seat(self):
        Ticket.objects.create(user=self.passenger,
                              trip=self.trip, seat=self.seat_1)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Ticket.objects.create(
                    user=self.passenger, trip=self.trip, seat=self.seat_1)

    def test_bus_and_route_deletion_blocked_when_trip_exists(self):
        with self.assertRaises(ProtectedError):
            self.bus.delete()

        with self.assertRaises(ProtectedError):
            self.route.delete()

    def test_deleting_trip_cascades_locations_tickets_and_payment(self):
        ticket = Ticket.objects.create(
            user=self.passenger, trip=self.trip, seat=self.seat_1)
        payment = Payment.objects.create(
            ticket=ticket, amount=Decimal("1200.00"), status=PaymentStatus.PAID)
        location = Location.objects.create(trip=self.trip, latitude=Decimal(
            "-1.292100"), longitude=Decimal("36.821900"))

        self.trip.delete()

        self.assertFalse(Ticket.objects.filter(pk=ticket.pk).exists())
        self.assertFalse(Payment.objects.filter(pk=payment.pk).exists())
        self.assertFalse(Location.objects.filter(pk=location.pk).exists())

    def test_ticket_status_choices_validate(self):
        ticket = Ticket(user=self.passenger, trip=self.trip,
                        seat=self.seat_1, status="INVALID")
        with self.assertRaises(ValidationError):
            ticket.full_clean()

        valid_ticket = Ticket(user=self.passenger, trip=self.trip,
                              seat=self.seat_1, status=TicketStatus.BOOKED)
        valid_ticket.full_clean()

    def test_payment_status_choices_validate(self):
        ticket = Ticket.objects.create(
            user=self.passenger, trip=self.trip, seat=self.seat_1)
        payment = Payment(ticket=ticket, amount=Decimal(
            "1400.00"), status="INVALID")

        with self.assertRaises(ValidationError):
            payment.full_clean()

        valid_payment = Payment(ticket=ticket, amount=Decimal(
            "1400.00"), status=PaymentStatus.PENDING)
        valid_payment.full_clean()

    def test_seat_from_different_bus_is_currently_allowed_for_ticket(self):
        other_bus = Bus.objects.create(plate_number="KBB-222B", capacity=40)
        other_seat = Seat.objects.create(bus=other_bus, seat_number="1")

        ticket = Ticket.objects.create(
            user=self.passenger, trip=self.trip, seat=other_seat)
        self.assertIsNotNone(ticket.pk)

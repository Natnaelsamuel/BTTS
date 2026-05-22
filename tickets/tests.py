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

from trips.models import TripStatus

from .models import Payment, PaymentStatus, Ticket, TicketStatus
from .ticket_lifecycle import (
    can_download_ticket,
    is_ticket_expired,
    sync_tickets_for_trip,
)


class StepTwoModelTests(TestCase):
    def setUp(self):
        self.driver = User.objects.create_user(
            username="driver1",
            email="driver1@example.com",
            password="password123",
            role=UserRole.DRIVER,
        )
        self.passenger = User.objects.create_user(
            username="passenger1",
            email="passenger1@example.com",
            password="password123",
            role=UserRole.PASSENGER,
        )

        self.bus = Bus.objects.create(plate_number="KAA-111A", capacity=50)
        self.seat_1 = Seat.objects.get(bus=self.bus, seat_number="1")

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
        other_seat = Seat.objects.get(bus=other_bus, seat_number="1")

        ticket = Ticket.objects.create(
            user=self.passenger, trip=self.trip, seat=other_seat)
        self.assertIsNotNone(ticket.pk)


class TicketLifecycleTests(TestCase):
    def setUp(self):
        self.driver = User.objects.create_user(
            username="driver_lc",
            email="driver_lc@example.com",
            password="password123",
            role=UserRole.DRIVER,
        )
        self.passenger = User.objects.create_user(
            username="passenger_lc",
            email="passenger_lc@example.com",
            password="password123",
            role=UserRole.PASSENGER,
        )
        self.bus = Bus.objects.create(plate_number="KAA-999Z", capacity=40)
        self.seat = Seat.objects.get(bus=self.bus, seat_number="1")
        self.route = Route.objects.create(
            origin="Addis Ababa",
            destination="Hawassa",
            distance=Decimal("275.00"),
        )
        departure = timezone.now() + timedelta(hours=2)
        self.trip = Trip.objects.create(
            bus=self.bus,
            route=self.route,
            departure_time=departure,
            arrival_time=departure + timedelta(hours=5),
            driver=self.driver,
        )
        self.ticket = Ticket.objects.create(
            user=self.passenger,
            trip=self.trip,
            seat=self.seat,
            status=TicketStatus.BOOKED,
        )

    def test_completed_trip_marks_booked_tickets_used(self):
        self.trip.status = TripStatus.COMPLETED
        self.trip.save(update_fields=["status", "updated_at"])
        updated = sync_tickets_for_trip(self.trip)

        self.assertEqual(updated, 1)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, TicketStatus.USED)
        self.assertTrue(is_ticket_expired(self.ticket))
        self.assertTrue(can_download_ticket(self.ticket))

    def test_cancelled_trip_cancels_active_tickets(self):
        self.trip.status = TripStatus.CANCELLED
        self.trip.save(update_fields=["status", "updated_at"])
        updated = sync_tickets_for_trip(self.trip)

        self.assertEqual(updated, 1)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, TicketStatus.CANCELLED)
        self.assertTrue(is_ticket_expired(self.ticket))
        self.assertFalse(can_download_ticket(self.ticket))

    def test_reserved_ticket_cannot_download_pdf(self):
        reserved = Ticket.objects.create(
            user=self.passenger,
            trip=self.trip,
            seat=Seat.objects.get(bus=self.bus, seat_number="2"),
            status=TicketStatus.RESERVED,
        )
        self.assertFalse(can_download_ticket(reserved))


class TicketPDFTests(TestCase):
    def setUp(self):
        self.driver = User.objects.create_user(
            username="driver_pdf",
            email="driver_pdf@example.com",
            password="password123",
            role=UserRole.DRIVER,
        )
        self.passenger = User.objects.create_user(
            username="passenger_pdf",
            email="passenger_pdf@example.com",
            password="password123",
            role=UserRole.PASSENGER,
            first_name="Abebe",
            last_name="Kebede",
        )
        self.bus = Bus.objects.create(plate_number="AA-12345", capacity=45)
        self.seat = Seat.objects.get(bus=self.bus, seat_number="12")
        self.route = Route.objects.create(
            origin="Addis Ababa",
            destination="Bahir Dar",
            distance=Decimal("510.00"),
        )
        departure = timezone.now() + timedelta(hours=3)
        self.trip = Trip.objects.create(
            bus=self.bus,
            route=self.route,
            departure_time=departure,
            arrival_time=departure + timedelta(hours=6),
            driver=self.driver,
            fare=Decimal("850.00"),
        )
        self.ticket = Ticket.objects.create(
            user=self.passenger,
            trip=self.trip,
            seat=self.seat,
            fare_amount=Decimal("850.00"),
            status=TicketStatus.BOOKED,
        )

    def test_pdf_generates_valid_document(self):
        from .ticket_pdf import build_ticket_pdf

        pdf_bytes = build_ticket_pdf(self.ticket)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreater(len(pdf_bytes), 1500)
        self.assertIn(f"BTTS Ticket {self.ticket.id}".encode(), pdf_bytes)

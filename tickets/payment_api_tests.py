# pylint: disable=no-member
# pyright: reportAttributeAccessIssue=false

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from buses.models import Bus, Seat
from routes.models import Route
from trips.models import Trip
from users.models import User, UserRole

from .models import PaymentStatus, Ticket, TicketStatus


class TicketPaymentAPITests(APITestCase):
    def setUp(self):
        self.driver = User.objects.create_user(
            username="driver_payment",
            email="driver_payment@example.com",
            password="strongPass123",
            role=UserRole.DRIVER,
        )
        self.passenger = User.objects.create_user(
            username="passenger_payment",
            email="passenger_payment@example.com",
            password="strongPass123",
            role=UserRole.PASSENGER,
        )

        self.bus = Bus.objects.create(plate_number="KPP-111P", capacity=20)
        self.seat_1 = Seat.objects.get(bus=self.bus, seat_number="1")
        self.route = Route.objects.create(
            origin="Addis Ababa", destination="Adama", distance=Decimal("100.00")
        )

        departure = timezone.now() + timedelta(hours=2)
        arrival = departure + timedelta(hours=2)
        self.trip = Trip.objects.create(
            bus=self.bus,
            route=self.route,
            departure_time=departure,
            arrival_time=arrival,
            fare=Decimal("250.00"),
            driver=self.driver,
        )

        self.ticket = Ticket.objects.create(
            user=self.passenger,
            trip=self.trip,
            seat=self.seat_1,
            status=TicketStatus.RESERVED,
            reserved_until=timezone.now() + timedelta(minutes=10),
        )

    @patch("tickets.views.initialize_chapa_payment")
    def test_passenger_can_initialize_payment(self, mock_initialize):
        mock_initialize.return_value = {
            "status": "success",
            "data": {
                "checkout_url": "https://checkout.chapa.co/pay/mock",
            },
        }

        self.client.force_authenticate(user=self.passenger)
        response = self.client.post(
            f"/api/passenger/tickets/{self.ticket.id}/pay/",
            {"return_url": "http://localhost:5173/result"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], PaymentStatus.PENDING)
        self.assertTrue(response.data["checkout_url"])

    @patch("tickets.webhook_views.verify_chapa_payment")
    def test_webhook_finalizes_ticket_as_booked_on_success(self, mock_verify):
        mock_verify.return_value = {
            "status": "success",
            "data": {"status": "success", "tx_ref": "tx-webhook-success"},
        }

        self.client.force_authenticate(user=self.passenger)
        with patch("tickets.views.initialize_chapa_payment") as mock_initialize:
            mock_initialize.return_value = {
                "status": "success",
                "data": {"checkout_url": "https://checkout.chapa.co/pay/mock"},
            }
            self.client.post(
                f"/api/passenger/tickets/{self.ticket.id}/pay/",
                {},
                format="json",
            )

        payment = self.ticket.payment
        payment.tx_ref = "tx-webhook-success"
        payment.save(update_fields=["tx_ref"])

        response = self.client.post(
            "/api/payments/chapa/webhook/",
            {"tx_ref": "tx-webhook-success"},
            HTTP_CHAPA_SIGNATURE=settings.CHAPA_WEBHOOK_SECRET,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.ticket.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.PAID)
        self.assertEqual(self.ticket.status, TicketStatus.BOOKED)

    @patch("tickets.webhook_views.verify_chapa_payment")
    def test_webhook_marks_ticket_cancelled_on_failed_payment(self, mock_verify):
        mock_verify.return_value = {
            "status": "success",
            "data": {"status": "failed", "tx_ref": "tx-webhook-failed"},
        }

        self.client.force_authenticate(user=self.passenger)
        with patch("tickets.views.initialize_chapa_payment") as mock_initialize:
            mock_initialize.return_value = {
                "status": "success",
                "data": {"checkout_url": "https://checkout.chapa.co/pay/mock"},
            }
            self.client.post(
                f"/api/passenger/tickets/{self.ticket.id}/pay/",
                {},
                format="json",
            )

        payment = self.ticket.payment
        payment.tx_ref = "tx-webhook-failed"
        payment.save(update_fields=["tx_ref"])

        response = self.client.post(
            "/api/payments/chapa/webhook/",
            {"tx_ref": "tx-webhook-failed"},
            HTTP_CHAPA_SIGNATURE=settings.CHAPA_WEBHOOK_SECRET,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.ticket.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.FAILED)
        self.assertEqual(self.ticket.status, TicketStatus.CANCELLED)

    @patch("tickets.views.verify_chapa_payment")
    def test_passenger_verify_endpoint_finalizes_as_paid(self, mock_verify):
        mock_verify.return_value = {
            "status": "success",
            "data": {"status": "success", "tx_ref": "tx-verify-success"},
        }

        self.client.force_authenticate(user=self.passenger)
        with patch("tickets.views.initialize_chapa_payment") as mock_initialize:
            mock_initialize.return_value = {
                "status": "success",
                "data": {"checkout_url": "https://checkout.chapa.co/pay/mock"},
            }
            self.client.post(
                f"/api/passenger/tickets/{self.ticket.id}/pay/",
                {},
                format="json",
            )

        payment = self.ticket.payment
        payment.tx_ref = "tx-verify-success"
        payment.save(update_fields=["tx_ref"])

        verify_response = self.client.post(
            f"/api/passenger/tickets/{self.ticket.id}/payment/verify/",
            {},
            format="json",
        )

        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.ticket.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.PAID)
        self.assertEqual(self.ticket.status, TicketStatus.BOOKED)

    @patch("tickets.views.verify_chapa_payment")
    def test_passenger_verify_endpoint_marks_failed_payment(self, mock_verify):
        mock_verify.return_value = {
            "status": "success",
            "data": {"status": "failed", "tx_ref": "tx-verify-failed"},
        }

        self.client.force_authenticate(user=self.passenger)
        with patch("tickets.views.initialize_chapa_payment") as mock_initialize:
            mock_initialize.return_value = {
                "status": "success",
                "data": {"checkout_url": "https://checkout.chapa.co/pay/mock"},
            }
            self.client.post(
                f"/api/passenger/tickets/{self.ticket.id}/pay/",
                {},
                format="json",
            )

        payment = self.ticket.payment
        payment.tx_ref = "tx-verify-failed"
        payment.save(update_fields=["tx_ref"])

        verify_response = self.client.post(
            f"/api/passenger/tickets/{self.ticket.id}/payment/verify/",
            {},
            format="json",
        )

        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.ticket.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.FAILED)
        self.assertEqual(self.ticket.status, TicketStatus.CANCELLED)

    @patch("tickets.views.verify_chapa_payment")
    def test_passenger_verify_endpoint_keeps_pending_as_reserved(self, mock_verify):
        mock_verify.return_value = {
            "status": "success",
            "data": {"status": "pending", "tx_ref": "tx-verify-pending"},
        }

        self.client.force_authenticate(user=self.passenger)
        with patch("tickets.views.initialize_chapa_payment") as mock_initialize:
            mock_initialize.return_value = {
                "status": "success",
                "data": {"checkout_url": "https://checkout.chapa.co/pay/mock"},
            }
            self.client.post(
                f"/api/passenger/tickets/{self.ticket.id}/pay/",
                {},
                format="json",
            )

        payment = self.ticket.payment
        payment.tx_ref = "tx-verify-pending"
        payment.save(update_fields=["tx_ref"])

        verify_response = self.client.post(
            f"/api/passenger/tickets/{self.ticket.id}/payment/verify/",
            {},
            format="json",
        )

        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.ticket.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.PENDING)
        self.assertEqual(self.ticket.status, TicketStatus.RESERVED)

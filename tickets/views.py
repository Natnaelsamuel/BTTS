# pylint: disable=no-member

from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.permissions import IsPassengerRole

from .chapa import initialize_chapa_payment, verify_chapa_payment
from .models import Payment, PaymentProvider, PaymentStatus, Ticket, TicketStatus
from .payment_service import finalize_payment_from_verify
from .serializers import (
    PaymentInitSerializer,
    PaymentSerializer,
    TicketBookingSerializer,
    TicketCancelSerializer,
    TicketSerializer,
)


class PassengerTicketViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated, IsPassengerRole]

    def get_serializer_class(self):
        if self.action == "create":
            return TicketBookingSerializer
        if self.action == "cancel_ticket":
            return TicketCancelSerializer
        if self.action == "initialize_payment":
            return PaymentInitSerializer
        if self.action == "get_payment":
            return PaymentSerializer
        if self.action == "verify_payment":
            return PaymentSerializer
        return TicketSerializer

    def get_queryset(self):
        return Ticket.objects.select_related("trip", "seat", "user").filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        _ = args, kwargs
        booking_serializer = TicketBookingSerializer(data=request.data)
        booking_serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                ticket = Ticket.objects.create(
                    user=request.user,
                    trip=booking_serializer.validated_data["trip"],
                    seat=booking_serializer.validated_data["seat"],
                    fare_amount=booking_serializer.validated_data["trip"].fare,
                    status=TicketStatus.RESERVED,
                    reserved_until=timezone.now()
                    + timedelta(minutes=settings.TICKET_RESERVATION_MINUTES),
                )
        except IntegrityError:
            return Response(
                {"detail": "This seat is already booked for the selected trip."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(TicketSerializer(ticket).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="pay")
    def initialize_payment(self, request, pk=None):
        _ = pk
        ticket = self.get_object()

        if ticket.status not in [TicketStatus.RESERVED, TicketStatus.BOOKED]:
            return Response(
                {"detail": "Payment is not allowed for this ticket status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if ticket.status == TicketStatus.RESERVED and ticket.reserved_until and ticket.reserved_until < timezone.now():
            ticket.status = TicketStatus.CANCELLED
            ticket.save(update_fields=["status", "updated_at"])
            return Response(
                {"detail": "Reservation expired. Please book again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        amount = ticket.fare_amount if ticket.fare_amount is not None else ticket.trip.fare
        if amount is None or amount <= 0:
            return Response(
                {"detail": "Trip fare is not configured. Contact support."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tx_ref = f"BTTS-{ticket.id}-{uuid4().hex[:8]}"
        return_url = serializer.validated_data.get("return_url") or "http://localhost:5173/payment-result"
        callback_url = request.build_absolute_uri(reverse("chapa_webhook"))

        try:
            chapa_response = initialize_chapa_payment(
                amount=amount,
                currency="ETB",
                email=request.user.email,
                first_name=request.user.first_name or request.user.username,
                last_name=request.user.last_name or "User",
                tx_ref=tx_ref,
                callback_url=callback_url,
                return_url=return_url,
            )
        except RuntimeError as exc:  # pragma: no cover
            return Response(
                {"detail": f"Failed to initialize Chapa payment: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        payment, _ = Payment.objects.update_or_create(
            ticket=ticket,
            defaults={
                "amount": amount,
                "currency": "ETB",
                "provider": PaymentProvider.CHAPA,
                "status": PaymentStatus.PENDING,
                "tx_ref": tx_ref,
                "checkout_url": (
                    chapa_response.get("data", {}).get("checkout_url")
                    or chapa_response.get("data", {}).get("checkoutLink")
                    or ""
                ),
                "raw_response": chapa_response,
            },
        )

        return Response(PaymentSerializer(payment).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="payment")
    def get_payment(self, request, pk=None):
        _ = request, pk
        ticket = self.get_object()
        payment = getattr(ticket, "payment", None)
        if payment is None:
            return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(PaymentSerializer(payment).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="payment/verify")
    def verify_payment(self, request, pk=None):
        _ = request, pk
        ticket = self.get_object()
        payment = getattr(ticket, "payment", None)
        if payment is None:
            return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)

        if payment.status == PaymentStatus.PAID:
            return Response(PaymentSerializer(payment).data, status=status.HTTP_200_OK)

        if not payment.tx_ref:
            return Response({"detail": "Payment transaction reference is missing."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            verify_response = verify_chapa_payment(payment.tx_ref)
        except RuntimeError as exc:  # pragma: no cover
            return Response(
                {"detail": f"Failed to verify Chapa payment: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        finalize_payment_from_verify(payment, verify_response)
        payment.refresh_from_db()
        return Response(PaymentSerializer(payment).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["patch"], url_path="cancel")
    def cancel_ticket(self, request, pk=None):
        _ = pk
        ticket = self.get_object()
        if ticket.status == TicketStatus.CANCELLED:
            return Response({"detail": "Ticket is already cancelled."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = TicketCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ticket.status = TicketStatus.CANCELLED
        ticket.save(update_fields=["status", "updated_at"])
        return Response(TicketSerializer(ticket).data, status=status.HTTP_200_OK)

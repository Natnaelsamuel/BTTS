import uuid

from django.db import models

from buses.models import Seat
from trips.models import Trip
from users.models import User


class TicketStatus(models.TextChoices):
    BOOKED = "BOOKED", "Booked"
    CANCELLED = "CANCELLED", "Cancelled"
    USED = "USED", "Used"


class PaymentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PAID = "PAID", "Paid"
    FAILED = "FAILED", "Failed"
    REFUNDED = "REFUNDED", "Refunded"


class Ticket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="tickets")
    trip = models.ForeignKey(
        Trip, on_delete=models.CASCADE, related_name="tickets")
    seat = models.ForeignKey(
        Seat, on_delete=models.PROTECT, related_name="tickets")
    status = models.CharField(
        max_length=20, choices=TicketStatus.choices, default=TicketStatus.BOOKED)
    booked_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-booked_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["trip", "seat"],
                condition=models.Q(status=TicketStatus.BOOKED),
                name="unique_trip_seat_ticket",
            ),
        ]

    def __str__(self) -> str:
        return f"Ticket {self.pk}"


class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.OneToOneField(
        Ticket, on_delete=models.CASCADE, related_name="payment")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Payment {self.pk} - {self.status}"

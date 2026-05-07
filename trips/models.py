import uuid

from django.db import models

from buses.models import Bus
from routes.models import Route
from users.models import User, UserRole


class TripStatus(models.TextChoices):
    SCHEDULED = "SCHEDULED", "Scheduled"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class Trip(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    bus = models.ForeignKey(
        Bus,
        on_delete=models.PROTECT,
        related_name="trips"
    )

    route = models.ForeignKey(
        Route,
        on_delete=models.PROTECT,
        related_name="trips"
    )

    driver = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="driven_trips",
        limit_choices_to={"role": UserRole.DRIVER},
    )

    departure_time = models.DateTimeField()

    arrival_time = models.DateTimeField()

    # ✅ TICKET PRICE FOR THIS SPECIFIC TRIP
    fare = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )

    status = models.CharField(
        max_length=20,
        choices=TripStatus.choices,
        default=TripStatus.SCHEDULED
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-departure_time"]

        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    arrival_time__gt=models.F("departure_time")
                ),
                name="trip_arrival_after_departure",
            ),
        ]

    def __str__(self):
        return (
            f"{self.route} | "
            f"{self.departure_time} | "
            f"Fare: {self.fare}"
        )
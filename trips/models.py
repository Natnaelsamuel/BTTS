from django.db import models

from buses.models import Bus
from routes.models import Route
from users.models import User, UserRole


class Trip(models.Model):
    bus = models.ForeignKey(
        Bus, on_delete=models.PROTECT, related_name="trips")
    route = models.ForeignKey(
        Route, on_delete=models.PROTECT, related_name="trips")
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    driver = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="driven_trips",
        limit_choices_to={"role": UserRole.DRIVER},
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-departure_time"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    arrival_time__gt=models.F("departure_time")),
                name="trip_arrival_after_departure",
            ),
        ]

    def __str__(self) -> str:
        return f"Trip {self.pk} ({self.departure_time})"

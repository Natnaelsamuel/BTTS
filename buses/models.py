# pylint: disable=no-member

from django.db import models


class Bus(models.Model):
    plate_number = models.CharField(max_length=30, unique=True)
    capacity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["plate_number"]

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new and self.capacity > 0:
            Seat.objects.bulk_create(
                [Seat(bus=self, seat_number=str(i))
                 for i in range(1, self.capacity + 1)]
            )

    def __str__(self) -> str:
        return str(self.plate_number)


class Seat(models.Model):
    bus = models.ForeignKey(
        Bus, on_delete=models.CASCADE, related_name="seats")
    seat_number = models.CharField(max_length=10)

    class Meta:
        ordering = ["bus", "seat_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["bus", "seat_number"], name="unique_bus_seat"),
        ]

    def __str__(self) -> str:
        return f"Seat {self.seat_number}"

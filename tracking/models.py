from django.db import models

from trips.models import Trip


class Location(models.Model):
    trip = models.ForeignKey(
        Trip, on_delete=models.CASCADE, related_name="locations")
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return f"Location {self.pk}"

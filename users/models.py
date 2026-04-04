from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    PASSENGER = "PASSENGER", "Passenger"
    DRIVER = "DRIVER", "Driver"


class User(AbstractUser):
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.PASSENGER,
        db_index=True,
    )

    def __str__(self) -> str:
        return f"{self.username} ({self.role})"

import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    PASSENGER = "PASSENGER", "Passenger"
    DRIVER = "DRIVER", "Driver"


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField("email address", unique=True)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.PASSENGER,
        db_index=True,
    )

    def __str__(self) -> str:
        return f"{self.username} ({self.role})"

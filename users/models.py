import uuid
from django.contrib.auth.hashers import make_password

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
    must_change_password = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.username} ({self.role})"


class PasswordResetOTP(models.Model):
    objects = models.Manager()
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="password_reset_otps")
    email = models.EmailField(db_index=True)
    otp_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def mark_otp(self, otp_code: str) -> None:
        self.otp_hash = make_password(otp_code)

    def __str__(self) -> str:
        return f"Password reset OTP for {self.email}"

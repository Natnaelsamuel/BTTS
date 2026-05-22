import uuid

from django.conf import settings
from django.db import models


class NotificationAudience(models.TextChoices):
    ALL = "ALL", "All Users"
    PASSENGER = "PASSENGER", "Passengers"
    DRIVER = "DRIVER", "Drivers"
    ADMIN = "ADMIN", "Admins"
    USER = "USER", "Single User"


class NotificationStatus(models.TextChoices):
    SENT = "SENT", "Sent"
    FAILED = "FAILED", "Failed"


class Notification(models.Model):
    objects = models.Manager()
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=160)
    message = models.TextField()
    audience = models.CharField(
        max_length=20, choices=NotificationAudience.choices, default=NotificationAudience.ALL)
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="targeted_notifications",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_notifications",
    )
    is_broadcast = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.audience})"


class NotificationDelivery(models.Model):
    objects = models.Manager()
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, related_name="deliveries")
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_deliveries",
    )
    status = models.CharField(
        max_length=20, choices=NotificationStatus.choices, default=NotificationStatus.SENT)
    delivered_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-delivered_at"]
        unique_together = [("notification", "recipient")]

    def __str__(self) -> str:
        return f"{self.notification_id} -> {self.recipient_id}"

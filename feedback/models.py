import uuid

from django.conf import settings
from django.db import models


class FeedbackCategory(models.TextChoices):
    SERVICE = "SERVICE", "Service"
    DRIVER = "DRIVER", "Driver"
    PAYMENT = "PAYMENT", "Payment"
    WEBSITE = "WEBSITE", "Website"
    SUGGESTION = "SUGGESTION", "Suggestion"
    COMPLAINT = "COMPLAINT", "Complaint"
    OTHER = "OTHER", "Other"


class Feedback(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="feedback_entries",
    )
    category = models.CharField(
        max_length=20, choices=FeedbackCategory.choices)
    subject = models.CharField(max_length=120)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.category}: {self.subject}"

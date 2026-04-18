from django.urls import path

from .webhook_views import ChapaWebhookAPIView

urlpatterns = [
    path("chapa/webhook/", ChapaWebhookAPIView.as_view(), name="chapa_webhook"),
]

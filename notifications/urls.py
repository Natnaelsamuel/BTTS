from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AdminNotificationLogAPIView, AdminNotificationViewSet

urlpatterns = [
    path("logs/", AdminNotificationLogAPIView.as_view(), name="admin-notification-logs"),
]

router = DefaultRouter()
router.register(r"", AdminNotificationViewSet, basename="admin-notifications")

urlpatterns += router.urls

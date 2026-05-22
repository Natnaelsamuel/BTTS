from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import IsAdminRole, IsPassengerOrDriverRole

from .models import Notification, NotificationAudience, NotificationDelivery, NotificationStatus
from .serializers import (
    NotificationCreateSerializer,
    NotificationDeliverySerializer,
    NotificationInboxSerializer,
    NotificationSerializer,
)

User = get_user_model()


def _recipients_for_audience(audience: str, target_user_id=None):
    if audience == NotificationAudience.ALL:
        return User.objects.all()
    if audience in {NotificationAudience.PASSENGER, NotificationAudience.DRIVER, NotificationAudience.ADMIN}:
        return User.objects.filter(role=audience)
    if audience == NotificationAudience.USER:
        return User.objects.filter(id=target_user_id)
    return User.objects.none()


class AdminNotificationViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]
    queryset = Notification.objects.select_related("target_user", "created_by").annotate(
        deliveries_count=Count("deliveries")
    )

    def get_serializer_class(self):
        if self.action == "create":
            return NotificationCreateSerializer
        return NotificationSerializer

    def perform_create(self, serializer):
        with transaction.atomic():
            notification = serializer.save(created_by=self.request.user)
            audience = notification.audience
            target_user_id = serializer.validated_data.get("target_user_id")
            recipients = _recipients_for_audience(
                audience, target_user_id=target_user_id)
            deliveries = [
                NotificationDelivery(
                    notification=notification,
                    recipient=user,
                    status=NotificationStatus.SENT,
                )
                for user in recipients
            ]
            NotificationDelivery.objects.bulk_create(deliveries)
            notification.is_broadcast = audience in {
                NotificationAudience.ALL, NotificationAudience.PASSENGER, NotificationAudience.DRIVER, NotificationAudience.ADMIN}
            notification.save(update_fields=["is_broadcast", "updated_at"])

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({"detail": "Notification created and sent."}, status=status.HTTP_201_CREATED)


class AdminNotificationLogAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def get(self, request):
        logs = NotificationDelivery.objects.select_related(
            "notification", "recipient", "notification__created_by")
        notification_id = request.query_params.get("notification_id")
        if notification_id:
            logs = logs.filter(notification_id=notification_id)
        data = NotificationDeliverySerializer(logs[:500], many=True).data
        return Response(data)


class UserNotificationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated, IsPassengerOrDriverRole]
    serializer_class = NotificationInboxSerializer

    def get_queryset(self):
        return NotificationDelivery.objects.select_related(
            "notification", "notification__created_by", "notification__target_user"
        ).filter(recipient=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        notification = self.get_object()
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at"])
        return Response(self.get_serializer(notification).data)

    @action(detail=True, methods=["patch"], url_path="read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at"])
        return Response(self.get_serializer(notification).data, status=status.HTTP_200_OK)

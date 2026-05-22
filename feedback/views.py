# pylint: disable=no-member

from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from users.permissions import IsPassengerRole
from users.permissions import IsAdminRole

from .models import Feedback
from .serializers import FeedbackCreateSerializer, FeedbackSerializer


class PassengerFeedbackViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated, IsPassengerRole]

    def get_queryset(self):
        return Feedback.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return FeedbackCreateSerializer
        return FeedbackSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AdminFeedbackViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAdminRole]
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer

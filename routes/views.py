# pylint: disable=no-member

from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from users.permissions import IsAdminRole

from .models import Route
from .serializers import RouteSerializer


class AdminRouteViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]

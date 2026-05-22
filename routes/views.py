"""Route admin API views."""

# pylint: disable=no-member

from django.db.models.deletion import ProtectedError
from rest_framework import mixins, viewsets
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.permissions import IsAdminRole

from .models import Route
from .serializers import RouteSerializer


class AdminRouteViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {
                    "detail": (
                        "Cannot delete this route because it has trips assigned to it."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

from rest_framework import serializers

from .models import Route


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ["id", "origin", "destination",
                  "distance", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

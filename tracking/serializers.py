from rest_framework import serializers

from .models import Location


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ["id", "trip", "latitude", "longitude", "timestamp"]
        read_only_fields = ["id", "trip", "timestamp"]


class LocationUpdateSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, min_value=-90, max_value=90)
    longitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, min_value=-180, max_value=180)

    def create(self, validated_data):
        raise NotImplementedError("LocationUpdateSerializer is input-only.")

    def update(self, instance, validated_data):
        raise NotImplementedError("LocationUpdateSerializer is input-only.")

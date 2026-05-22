from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Notification, NotificationDelivery, NotificationAudience

User = get_user_model()


class NotificationUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "role"]


class NotificationSerializer(serializers.ModelSerializer):
    audience_label = serializers.CharField(
        source="get_audience_display", read_only=True)
    target_user = NotificationUserSerializer(read_only=True)
    created_by = NotificationUserSerializer(read_only=True)
    deliveries_count = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "title",
            "message",
            "audience",
            "audience_label",
            "target_user",
            "created_by",
            "is_broadcast",
            "deliveries_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "audience_label",
            "target_user",
            "created_by",
            "is_broadcast",
            "deliveries_count",
            "created_at",
            "updated_at",
        ]

    def get_deliveries_count(self, obj):
        return getattr(obj, "deliveries_count", obj.deliveries.count())


class NotificationCreateSerializer(serializers.ModelSerializer):
    target_user_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = Notification
        fields = ["title", "message", "audience", "target_user_id"]

    def validate(self, attrs):
        audience = attrs.get("audience")
        target_user_id = attrs.get("target_user_id")
        if audience == NotificationAudience.USER and not target_user_id:
            raise serializers.ValidationError(
                {"target_user_id": "This field is required when audience is USER."})
        if audience != NotificationAudience.USER and target_user_id:
            raise serializers.ValidationError(
                {"target_user_id": "Only single-user notifications can include a target user."})
        if audience == NotificationAudience.USER and target_user_id and not User.objects.filter(id=target_user_id).exists():
            raise serializers.ValidationError(
                {"target_user_id": "Selected user does not exist."})
        return attrs

    def create(self, validated_data):
        target_user_id = validated_data.pop("target_user_id", None)
        if target_user_id:
            validated_data["target_user"] = User.objects.filter(
                id=target_user_id).first()
        return Notification.objects.create(**validated_data)


class NotificationDeliverySerializer(serializers.ModelSerializer):
    notification = NotificationSerializer(read_only=True)
    recipient = NotificationUserSerializer(read_only=True)

    class Meta:
        model = NotificationDelivery
        fields = ["id", "notification", "recipient",
                  "status", "delivered_at", "read_at"]
        read_only_fields = fields


class NotificationInboxSerializer(serializers.ModelSerializer):
    notification = NotificationSerializer(read_only=True)

    class Meta:
        model = NotificationDelivery
        fields = ["id", "notification", "status", "delivered_at", "read_at"]
        read_only_fields = fields

from rest_framework import serializers

from .models import Feedback, FeedbackCategory


class FeedbackSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(
        source="get_category_display", read_only=True)
    user = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Feedback
        fields = [
            "id",
            "category",
            "category_label",
            "user",
            "subject",
            "message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "category_label", "created_at", "updated_at"]

    def get_user(self, obj):
        return {
            "id": str(obj.user.id),
            "username": obj.user.username,
            "email": obj.user.email,
        }


class FeedbackCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ["category", "subject", "message"]

    def validate_category(self, value):
        allowed = {choice[0] for choice in FeedbackCategory.choices}
        if value not in allowed:
            raise serializers.ValidationError("Invalid feedback category.")
        return value

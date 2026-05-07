# pyright: reportAbstractUsage=false

from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

from .models import UserRole

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    username = serializers.CharField(required=True, allow_blank=False)
    email = serializers.EmailField(required=True, allow_blank=False)
    first_name = serializers.CharField(required=True, allow_blank=False)
    last_name = serializers.CharField(required=True, allow_blank=False)
    role = serializers.ChoiceField(
        choices=UserRole.choices,
        required=True
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
            "role",
        ]
        read_only_fields = ["id"]

    def validate_role(self, value):
        if value == UserRole.ADMIN:
            raise serializers.ValidationError("Admin accounts cannot be self-registered.")
        return value

    def validate(self, data):
        if not data.get("username"):
            raise serializers.ValidationError({"username": "Username is required"})
        if not data.get("email"):
            raise serializers.ValidationError({"email": "Email is required"})
        if not data.get("password"):
            raise serializers.ValidationError({"password": "Password is required"})
        return data

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role"]


class LoginResponseSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    access = serializers.CharField()
    user = UserSummarySerializer()

    def create(self, validated_data):
        raise NotImplementedError("LoginResponseSerializer is output-only.")

    def update(self, instance, validated_data):
        raise NotImplementedError("LoginResponseSerializer is output-only.")


class CustomTokenObtainPairSerializer(serializers.Serializer):
    username = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        username = attrs.get("username")
        password = attrs.get("password")

        if email and not username:
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist as exc:
                raise AuthenticationFailed(
                    "No active account found with the given credentials") from exc
            username = user.username
        elif not username:
            raise serializers.ValidationError(
                {"username": "Provide either username or email to login."}
            )

        user = authenticate(
            request=self.context.get("request"),
            username=username,
            password=password,
        )
        if not user:
            raise AuthenticationFailed(
                "No active account found with the given credentials")

        refresh = RefreshToken.for_user(user)
        refresh["role"] = user.role
        refresh["username"] = user.username

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": UserSummarySerializer(user).data,
        }

    def create(self, validated_data):
        raise NotImplementedError(
            "CustomTokenObtainPairSerializer does not support create().")

    def update(self, instance, validated_data):
        raise NotImplementedError(
            "CustomTokenObtainPairSerializer does not support update().")

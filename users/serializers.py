# pyright: reportAbstractUsage=false

from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

from .models import UserRole

User = get_user_model()


def _raise_password_validation_error(password: str, user=None, field_name: str = "password") -> None:
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError({field_name: exc.messages}) from exc


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password",
                  "first_name", "last_name", "role"]
        read_only_fields = ["id"]
        extra_kwargs = {
            "email": {"required": True},
        }

    def validate_role(self, value):
        request = self.context.get("request")
        # Prevent self-registration as ADMIN or DRIVER by non-admin users.
        if value == UserRole.ADMIN:
            raise serializers.ValidationError(
                "Admin accounts cannot be self-registered.")
        if value == UserRole.DRIVER:
            # allow only when request is from an authenticated admin
            if not request or not getattr(request, "user", None) or not getattr(request.user, "is_authenticated", False):
                raise serializers.ValidationError(
                    "Driver accounts cannot be self-registered. Contact an administrator.")
            if getattr(request.user, "role", None) != UserRole.ADMIN:
                raise serializers.ValidationError(
                    "Driver accounts can only be created by an administrator.")
        return value

    def validate(self, attrs):
        candidate = User(
            username=attrs.get("username", ""),
            email=attrs.get("email", ""),
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
        )
        _raise_password_validation_error(attrs["password"], user=candidate)
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name",
                  "last_name", "role", "is_active", "must_change_password"]


class UserDetailUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name",
                  "last_name", "role", "is_active", "must_change_password"]
        read_only_fields = ["id", "username", "email", "role"]


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "must_change_password",
        ]
        read_only_fields = ["role", "is_active", "must_change_password"]


class LoginResponseSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    access = serializers.CharField()
    user = UserSummarySerializer()

    def create(self, validated_data):
        raise NotImplementedError("LoginResponseSerializer is output-only.")

    def update(self, instance, validated_data):
        raise NotImplementedError("LoginResponseSerializer is output-only.")


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def create(self, validated_data):
        raise NotImplementedError(
            "PasswordResetRequestSerializer is input-only.")

    def update(self, instance, validated_data):
        raise NotImplementedError(
            "PasswordResetRequestSerializer is input-only.")


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(min_length=4, max_length=8)
    new_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, attrs):
        candidate = User(email=attrs.get("email", ""))
        _raise_password_validation_error(attrs["new_password"], user=candidate, field_name="new_password")
        return attrs

    def create(self, validated_data):
        raise NotImplementedError(
            "PasswordResetConfirmSerializer is input-only.")

    def update(self, instance, validated_data):
        raise NotImplementedError(
            "PasswordResetConfirmSerializer is input-only.")


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, attrs):
        _raise_password_validation_error(
            attrs["new_password"],
            user=self.context.get("user"),
            field_name="new_password",
        )
        return attrs

    def create(self, validated_data):
        raise NotImplementedError(
            "ChangePasswordSerializer is input-only.")

    def update(self, instance, validated_data):
        raise NotImplementedError(
            "ChangePasswordSerializer is input-only.")


class ForcePasswordResetSerializer(serializers.Serializer):
    new_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, attrs):
        _raise_password_validation_error(
            attrs["new_password"],
            user=self.context.get("user"),
            field_name="new_password",
        )
        return attrs

    def create(self, validated_data):
        raise NotImplementedError(
            "ForcePasswordResetSerializer is input-only.")

    def update(self, instance, validated_data):
        raise NotImplementedError(
            "ForcePasswordResetSerializer is input-only.")


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

        # Check if the account has been deactivated by admin
        if not user.is_active:
            raise AuthenticationFailed(
                "Your account has been deactivated by the administrator. Please contact support.")

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

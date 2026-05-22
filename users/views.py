from .models import PasswordResetOTP
import random
import logging
from datetime import timedelta
from smtplib import SMTPConnectError, SMTPDataError, SMTPRecipientsRefused, SMTPSenderRefused

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, extend_schema, inline_serializer
from rest_framework import generics, permissions
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .permissions import IsAdminRole, IsDriverRole
from .serializers import (
    CustomTokenObtainPairSerializer,
    ChangePasswordSerializer,
    LoginResponseSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ForcePasswordResetSerializer,
    RegisterSerializer,
    UserSummarySerializer,
    UserDetailUpdateSerializer,
    ProfileUpdateSerializer,
)

User = get_user_model()

logger = logging.getLogger(__name__)


@extend_schema(
    request=RegisterSerializer,
    responses={201: UserSummarySerializer},
    examples=[
        OpenApiExample(
            "Passenger Register",
            value={
                "username": "passenger101",
                "email": "passenger101@example.com",
                "password": "strongPass123",
                "first_name": "Jane",
                "last_name": "Doe",
                "role": "PASSENGER",
            },
            request_only=True,
        ),
        OpenApiExample(
            "Driver Register",
            value={
                "username": "driver101",
                "email": "driver101@example.com",
                "password": "strongPass123",
                "first_name": "John",
                "last_name": "Doe",
                "role": "DRIVER",
            },
            request_only=True,
        ),
    ],
)
class RegisterAPIView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class LoginAPIView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    @extend_schema(
        request=CustomTokenObtainPairSerializer,
        responses={200: LoginResponseSerializer},
        examples=[
            OpenApiExample(
                "Login with Username",
                value={
                    "username": "driver001",
                    "password": "strongPass123",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Login with Email",
                value={
                    "email": "driver001@example.com",
                    "password": "strongPass123",
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class MeAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer(self, *args, **kwargs):
        kwargs.setdefault("partial", True)
        return super().get_serializer(*args, **kwargs)


class UserListAPIView(generics.ListAPIView):
    serializer_class = UserSummarySerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def get_queryset(self):
        queryset = self.request.user.__class__.objects.all().order_by("id")

        role = self.request.query_params.get("role")
        if role:
            queryset = queryset.filter(role=role)

        return queryset


class UserSearchAPIView(generics.ListAPIView):
    serializer_class = UserSummarySerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def get_queryset(self):
        queryset = self.request.user.__class__.objects.all().order_by("id")

        query = self.request.query_params.get("q", "").strip()
        role = self.request.query_params.get("role")

        if query:
            queryset = queryset.filter(
                Q(username__icontains=query)
                | Q(email__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
            )

        if role:
            queryset = queryset.filter(role=role)

        return queryset


class AdminOnlyCheckAPIView(APIView):
    permission_classes = [IsAdminRole]

    @extend_schema(
        responses={
            200: inline_serializer(
                name="AdminCheckResponse",
                fields={"detail": serializers.CharField()},
            )
        }
    )
    def get(self, _request):
        return Response({"detail": "Admin access granted."})


class DriverOnlyCheckAPIView(APIView):
    permission_classes = [IsDriverRole]

    @extend_schema(
        responses={
            200: inline_serializer(
                name="DriverCheckResponse",
                fields={"detail": serializers.CharField()},
            )
        }
    )
    def get(self, _request):
        return Response({"detail": "Driver access granted."})


class PasswordResetRequestAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(request=PasswordResetRequestSerializer, responses={200: inline_serializer(
        name="PasswordResetRequestResponse",
        fields={"detail": serializers.CharField()},
    )})
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].strip().lower()
        user = User.objects.filter(email__iexact=email).first()

        if not user or not user.email:
            return Response(
                {"detail": "No account found for that email address."},
                status=404,
            )

        otp_code = f"{random.randint(0, 999999):06d}"
        PasswordResetOTP.objects.filter(
            user=user, used_at__isnull=True).delete()
        otp_record = PasswordResetOTP.objects.create(
            user=user,
            email=user.email,
            expires_at=timezone.now() + timedelta(minutes=settings.PASSWORD_RESET_OTP_MINUTES),
            otp_hash=make_password(otp_code),
        )
        otp_record.save(update_fields=["otp_hash", "updated_at"])

        try:
            logger.info("Sending password reset OTP to %s", user.email)
            send_mail(
                subject="Your BTTS password reset code",
                message=(
                    f"Hello {user.username},\n\n"
                    f"Your one-time password reset code is: {otp_code}\n\n"
                    f"This code expires in {settings.PASSWORD_RESET_OTP_MINUTES} minutes.\n\n"
                    "If you did not request this, you can safely ignore this email."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except (SMTPRecipientsRefused, SMTPSenderRefused, SMTPDataError, SMTPConnectError):
            logger.exception("Failed to send OTP email to %s", user.email)
            return Response(
                {"detail": "Could not send OTP email because the mail settings are invalid."},
                status=500,
            )

        return Response(
            {"detail": "OTP has been sent to your registered email address."},
            status=200,
        )


class PasswordResetConfirmAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(request=PasswordResetConfirmSerializer, responses={200: inline_serializer(
        name="PasswordResetConfirmResponse",
        fields={"detail": serializers.CharField()},
    )})
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].strip().lower()
        otp = serializer.validated_data["otp"].strip()
        user = User.objects.filter(email__iexact=email).first()

        if not user:
            return Response({"detail": "Invalid OTP or email."}, status=400)

        otp_record = PasswordResetOTP.objects.filter(
            user=user,
            email__iexact=email,
            used_at__isnull=True,
        ).first()

        if not otp_record:
            return Response({"detail": "OTP has expired or is invalid."}, status=400)

        if otp_record.expires_at < timezone.now():
            otp_record.delete()
            return Response({"detail": "OTP has expired. Please request a new one."}, status=400)

        if not check_password(otp, otp_record.otp_hash):
            otp_record.attempts += 1
            otp_record.save(update_fields=["attempts", "updated_at"])
            return Response({"detail": "Invalid OTP."}, status=400)

        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        otp_record.used_at = timezone.now()
        otp_record.save(update_fields=["used_at", "updated_at"])

        return Response({"detail": "Password has been reset successfully."}, status=200)


class ChangePasswordAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=ChangePasswordSerializer, responses={200: inline_serializer(
        name="ChangePasswordResponse",
        fields={"detail": serializers.CharField()},
    )})
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        current_password = serializer.validated_data["current_password"]
        new_password = serializer.validated_data["new_password"]

        if not user.check_password(current_password):
            return Response({"detail": "Current password is incorrect."}, status=400)

        user.set_password(new_password)
        if getattr(user, "must_change_password", False):
            user.must_change_password = False
            user.save(update_fields=["password", "must_change_password"])
        else:
            user.save(update_fields=["password"])

        return Response({"detail": "Password changed successfully."}, status=200)


class ForcePasswordResetAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=ForcePasswordResetSerializer, responses={200: inline_serializer(
        name="ForcePasswordResetResponse",
        fields={"detail": serializers.CharField(
        ), "user": UserSummarySerializer()},
    )})
    def post(self, request):
        serializer = ForcePasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not getattr(user, "must_change_password", False):
            return Response({"detail": "Password reset is not required."}, status=400)

        user.set_password(serializer.validated_data["new_password"])
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password"])

        return Response(
            {
                "detail": "Password updated successfully.",
                "user": UserSummarySerializer(user).data,
            },
            status=200,
        )


class UserDetailAPIView(generics.UpdateAPIView):
    """Allow admins to update user details (is_active status)."""
    queryset = User.objects.all()
    serializer_class = UserDetailUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]
    lookup_field = "id"

    def get_serializer(self, *args, **kwargs):
        """Override to enable partial updates (PATCH)."""
        kwargs.setdefault("partial", True)
        return super().get_serializer(*args, **kwargs)


class AdminCreateDriverAPIView(generics.CreateAPIView):
    """Admin-only endpoint to create driver accounts.

    Creates a driver user with a temporary password and emails that password so
    the driver can log in and change it after the first sign-in.
    """
    serializer_class = RegisterSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def post(self, request, *args, **kwargs):
        data = dict(request.data)
        # force role to DRIVER regardless of client input
        data["role"] = "DRIVER"

        # generate a temporary password if not provided
        temp_password = data.get("password")
        if not temp_password:
            import secrets
            temp_password = secrets.token_urlsafe(12)
            data["password"] = temp_password

        serializer = self.get_serializer(
            data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # keep the account active so the driver can sign in with the temp password
        user.is_active = True
        user.must_change_password = True
        user.save(update_fields=["is_active", "must_change_password"])

        # send the temporary password directly to the driver
        try:
            logger.info("Sending driver temporary password to %s", user.email)
            send_mail(
                subject="BTTS: Your temporary driver password",
                message=(
                    f"Hello {user.first_name or user.username},\n\n"
                    f"An administrator created a driver account for you.\n\n"
                    f"Your temporary password is: {temp_password}\n\n"
                    "Sign in with this password, then change it immediately from the Change Password page.\n\n"
                    "If you did not expect this, please contact support."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except (SMTPRecipientsRefused, SMTPSenderRefused, SMTPDataError, SMTPConnectError):
            logger.exception(
                "Failed to send driver temporary password email to %s", user.email)

        return Response(UserSummarySerializer(user).data, status=201)

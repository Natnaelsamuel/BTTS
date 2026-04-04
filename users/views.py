from django.db.models import Q
from drf_spectacular.utils import OpenApiExample, extend_schema, inline_serializer
from rest_framework import generics, permissions
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .permissions import IsAdminRole, IsDriverRole
from .serializers import (
    CustomTokenObtainPairSerializer,
    LoginResponseSerializer,
    RegisterSerializer,
    UserSummarySerializer,
)


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


class MeAPIView(generics.RetrieveAPIView):
    serializer_class = UserSummarySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


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

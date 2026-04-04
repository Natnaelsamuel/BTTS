from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .views import (
    AdminOnlyCheckAPIView,
    DriverOnlyCheckAPIView,
    LoginAPIView,
    MeAPIView,
    RegisterAPIView,
)

urlpatterns = [
    path("register/", RegisterAPIView.as_view(), name="register"),
    path("login/", LoginAPIView.as_view(), name="login"),
    path("me/", MeAPIView.as_view(), name="me"),
    path("admin-check/", AdminOnlyCheckAPIView.as_view(), name="admin_check"),
    path("driver-check/", DriverOnlyCheckAPIView.as_view(), name="driver_check"),
    path("token/", LoginAPIView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
]

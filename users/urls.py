from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .views import (
    AdminOnlyCheckAPIView,
    AdminCreateDriverAPIView,
    ChangePasswordAPIView,
    DriverOnlyCheckAPIView,
    LoginAPIView,
    PasswordResetConfirmAPIView,
    PasswordResetRequestAPIView,
    ForcePasswordResetAPIView,
    MeAPIView,
    RegisterAPIView,
    UserListAPIView,
    UserSearchAPIView,
    UserDetailAPIView,
)

urlpatterns = [
    path("register/", RegisterAPIView.as_view(), name="register"),
    path("login/", LoginAPIView.as_view(), name="login"),
    path("password-reset/", PasswordResetRequestAPIView.as_view(),
         name="password_reset_request"),
    path("password-reset/confirm/", PasswordResetConfirmAPIView.as_view(),
         name="password_reset_confirm"),
    path("password-reset/force/", ForcePasswordResetAPIView.as_view(),
         name="password_reset_force"),
    path("change-password/", ChangePasswordAPIView.as_view(), name="change_password"),
    path("me/", MeAPIView.as_view(), name="me"),
    path("users/", UserListAPIView.as_view(), name="users_list"),
    path("users/<uuid:id>/", UserDetailAPIView.as_view(), name="user_detail"),
    path("users/search/", UserSearchAPIView.as_view(), name="users_search"),
    path("admin-check/", AdminOnlyCheckAPIView.as_view(), name="admin_check"),
    path("driver-check/", DriverOnlyCheckAPIView.as_view(), name="driver_check"),
    path("admin/create-driver/", AdminCreateDriverAPIView.as_view(),
         name="admin_create_driver"),
    path("token/", LoginAPIView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
]

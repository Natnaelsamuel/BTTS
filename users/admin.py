from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import PasswordResetOTP, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "id",
        "username",
        "email",
        "role",
        "is_staff",
        "is_active",
        "must_change_password",
    )
    list_filter = ("role", "is_staff", "is_active", "must_change_password")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("username",)
    fieldsets = UserAdmin.fieldsets + (
        ("Zemen Bus", {"fields": ("role", "must_change_password")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "password1",
                    "password2",
                    "role",
                    "must_change_password",
                ),
            },
        ),
    )


@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = ("email", "user", "expires_at", "used_at", "attempts", "created_at")
    list_filter = ("used_at",)
    search_fields = ("email", "user__username", "user__email")
    readonly_fields = ("otp_hash", "created_at", "updated_at")

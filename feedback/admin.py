from django.contrib import admin

from .models import Feedback


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("subject", "category", "user", "created_at")
    list_filter = ("category", "created_at")
    search_fields = ("subject", "message", "user__username", "user__email")

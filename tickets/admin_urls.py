from django.urls import path

from .views import AdminAnalyticsAPIView, AdminAnalyticsExportAPIView

urlpatterns = [
    path("", AdminAnalyticsAPIView.as_view(), name="admin_analytics"),
    path("export/", AdminAnalyticsExportAPIView.as_view(), name="admin_analytics_export"),
]

from rest_framework.routers import DefaultRouter

from .views import UserNotificationViewSet

router = DefaultRouter()
router.register(r"", UserNotificationViewSet, basename="user-notifications")

urlpatterns = router.urls

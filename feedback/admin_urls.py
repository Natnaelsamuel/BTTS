from rest_framework.routers import DefaultRouter

from .views import AdminFeedbackViewSet

router = DefaultRouter()
router.register(r"", AdminFeedbackViewSet, basename="admin-feedback")

urlpatterns = router.urls

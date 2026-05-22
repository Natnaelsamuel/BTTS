from rest_framework.routers import DefaultRouter

from .views import PassengerFeedbackViewSet

router = DefaultRouter()
router.register(r"", PassengerFeedbackViewSet, basename="passenger-feedback")

urlpatterns = router.urls

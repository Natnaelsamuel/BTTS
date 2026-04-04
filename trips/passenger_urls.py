from rest_framework.routers import DefaultRouter

from .views import PassengerTripViewSet

router = DefaultRouter()
router.register(r"", PassengerTripViewSet, basename="passenger-trips")

urlpatterns = router.urls

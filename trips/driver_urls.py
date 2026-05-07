from rest_framework.routers import DefaultRouter

from .views import DriverAssignedTripViewSet

router = DefaultRouter()
router.register(r"", DriverAssignedTripViewSet, basename="driver-trips")

urlpatterns = router.urls

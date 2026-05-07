from rest_framework.routers import DefaultRouter

from .views import AdminTripViewSet

router = DefaultRouter()
router.register(r"", AdminTripViewSet, basename="admin-trips")

urlpatterns = router.urls

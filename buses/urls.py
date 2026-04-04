from rest_framework.routers import DefaultRouter

from .views import AdminBusViewSet

router = DefaultRouter()
router.register(r"", AdminBusViewSet, basename="admin-buses")

urlpatterns = router.urls

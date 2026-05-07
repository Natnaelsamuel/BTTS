from rest_framework.routers import DefaultRouter

from .views import AdminRouteViewSet

router = DefaultRouter()
router.register(r"", AdminRouteViewSet, basename="admin-routes")

urlpatterns = router.urls

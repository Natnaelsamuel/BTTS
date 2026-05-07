from rest_framework.routers import DefaultRouter

from .views import PassengerTicketViewSet

router = DefaultRouter()
router.register(r"", PassengerTicketViewSet, basename="passenger-tickets")

urlpatterns = router.urls

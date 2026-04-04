from django.urls import path

from .views import BusSeatListAPIView

urlpatterns = [
    path("<int:bus_id>/seats/", BusSeatListAPIView.as_view(), name="bus_seat_list"),
]

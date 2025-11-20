from django.urls import path
from .views import AquariumSVGView

urlpatterns = [
    path("svg/", AquariumSVGView.as_view(), name="aquarium-svg"),
]

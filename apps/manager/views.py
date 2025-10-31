from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, permissions
from .models import FishSpecies, ShopItem, Aquarium, FishTank
from .serializers import (
    FishSpeciesSerializer,
    ShopItemSerializer,
    AquariumSerializer,
    FishTankSerializer,
)

class FishSpeciesViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FishSpecies.objects.filter(active=True).select_related("asset")
    serializer_class = FishSpeciesSerializer
    permission_classes = [permissions.AllowAny]

class ShopItemViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ShopItem.objects.filter(active=True).select_related("fish", "background")
    serializer_class = ShopItemSerializer
    permission_classes = [permissions.AllowAny]

class MyAquariumViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AquariumSerializer
    def get_queryset(self):
        return Aquarium.objects.filter(owner=self.request.user)

class MyFishTankViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FishTankSerializer
    def get_queryset(self):
        return FishTank.objects.filter(owner=self.request.user).select_related("repository")

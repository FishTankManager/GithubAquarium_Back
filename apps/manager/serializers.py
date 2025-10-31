from rest_framework import serializers
from .models import SvgAsset, FishSpecies, ShopItem, Aquarium, FishTank

class SvgAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = SvgAsset
        fields = ["id", "name", "asset_type", "svg", "width_px", "height_px"]

class FishSpeciesSerializer(serializers.ModelSerializer):
    asset = SvgAssetSerializer()
    class Meta:
        model = FishSpecies
        fields = ["id", "name", "rarity", "base_price", "asset"]

class ShopItemSerializer(serializers.ModelSerializer):
    fish = FishSpeciesSerializer()
    # background도 필요하면 serializer로
    class Meta:
        model = ShopItem
        fields = ["id", "item_type", "price", "active", "fish", "background"]

class AquariumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Aquarium
        fields = ["id", "background", "created_at"]

class FishTankSerializer(serializers.ModelSerializer):
    repository_name = serializers.CharField(source="repository.full_name", read_only=True)
    class Meta:
        model = FishTank
        fields = ["id", "repository", "repository_name", "background", "contributor_count"]

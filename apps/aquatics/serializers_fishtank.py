# apps/aquatics/serializers_fishtank.py
from rest_framework import serializers
from apps.aquatics.models import Fishtank, ContributionFish
from apps.repositories.models import Contributor
from apps.items.models import Background


class FishSpeciesSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    maturity = serializers.IntegerField()
    required_commits = serializers.IntegerField()
    svg_template = serializers.CharField()


class ContributionFishSerializer(serializers.ModelSerializer):
    species = serializers.SerializerMethodField()

    class Meta:
        model = ContributionFish
        fields = ["id", "is_visible_in_fishtank", "species"]

    def get_species(self, obj):
        s = obj.fish_species
        return {
            "id": s.id,
            "name": s.name,
            "maturity": s.maturity,
            "required_commits": s.required_commits,
            "svg_template": s.svg_template,
        }


class ContributorSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source="user.username")
    fish = ContributionFishSerializer(source="contribution_fish", read_only=True)

    class Meta:
        model = Contributor
        fields = ["id", "user", "commit_count", "fish"]


class FishtankDetailSerializer(serializers.ModelSerializer):
    repository = serializers.CharField(source="repository.name")
    contributors = ContributorSerializer(source="repository.contributors", many=True)

    class Meta:
        model = Fishtank
        fields = ["id", "repository", "svg_path", "contributors"]


class FishtankBackgroundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Background
        fields = ["id", "name", "code", "background_image"]

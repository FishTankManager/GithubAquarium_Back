#aqutatics/serializers_aquarium.py
from rest_framework import serializers
from apps.aquatics.models import Aquarium, ContributionFish, OwnBackground


class AquariumFishSerializer(serializers.ModelSerializer):
    species = serializers.SerializerMethodField()
    repository = serializers.SerializerMethodField()
    my_commit_count = serializers.SerializerMethodField()
    unlocked_at = serializers.SerializerMethodField()

    class Meta:
        model = ContributionFish
        fields = [
            "id",
            "species",
            "repository",
            "my_commit_count",
            "unlocked_at",
        ]

    def get_species(self, obj):
        s = obj.fish_species
        return {
            "id": s.id,
            "name": s.name,
            "maturity": s.maturity,
            "required_commits": s.required_commits,
            "svg_template": s.svg_template,
        }

    def get_repository(self, obj):
        repo = obj.contributor.repository
        return {
            "id": repo.id,
            "name": repo.name,
        }

    def get_my_commit_count(self, obj):
        return obj.contributor.commit_count

    def get_unlocked_at(self, obj):
        # ContributionFish는 unlocked_at을 직접 갖지 않으므로 UnlockedFish에서 조회
        unlocked = obj.contributor.user.owned_fishes.filter(
            fish_species=obj.fish_species
        ).first()
        return unlocked.unlocked_at if unlocked else None


class AquariumDetailSerializer(serializers.ModelSerializer):
    background = serializers.SerializerMethodField()
    fishes = AquariumFishSerializer(many=True)

    class Meta:
        model = Aquarium
        fields = ["background", "svg_path", "fishes"]

    def get_background(self, obj):
        if obj.background:
            return {
                "id": obj.background.id,
                "name": obj.background.background.name,
                "svg_template": obj.background.background.svg_template,
            }
        return None


class AquariumBackgroundSerializer(serializers.ModelSerializer):
    class Meta:
        model = OwnBackground
        fields = ["id", "background", "unlocked_at"]

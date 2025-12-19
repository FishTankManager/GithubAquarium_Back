# apps/aquatics/serializers.py
from rest_framework import serializers
from django.conf import settings
from .models import Aquarium, Fishtank, ContributionFish, UnlockedFish, OwnBackground
from drf_yasg.utils import swagger_serializer_method

class FishSerializer(serializers.ModelSerializer):
    """아쿠아리움/피시탱크 내부 물고기 상세 정보"""
    name = serializers.CharField(source='fish_species.name', read_only=True)
    group_code = serializers.CharField(source='fish_species.group_code', read_only=True)
    maturity = serializers.IntegerField(source='fish_species.maturity', read_only=True)
    repository_name = serializers.CharField(source='contributor.repository.full_name', read_only=True)
    commit_count = serializers.IntegerField(source='contributor.commit_count', read_only=True)
    unlocked_at = serializers.SerializerMethodField()

    class Meta:
        model = ContributionFish
        fields = [
            'id', 'name', 'group_code', 'maturity', 
            'repository_name', 'commit_count', 
            'unlocked_at', 'is_visible_in_aquarium', 'is_visible_in_fishtank'
        ]

    def get_unlocked_at(self, obj):
        """
        N+1 방지 로직:
        Context에 미리 로딩된 unlocked_map이 있으면 그것을 사용하고,
        없으면 DB를 조회합니다.
        """
        # 1. Context에서 캐시 확인 (최적화)
        unlocked_map = self.context.get('unlocked_map')
        if unlocked_map is not None:
            return unlocked_map.get(obj.fish_species_id)

        # 2. 캐시가 없으면 DB 조회 (기본 동작)
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        
        unlocked_record = UnlockedFish.objects.filter(
            user=request.user, 
            fish_species_id=obj.fish_species_id
        ).first()
        return unlocked_record.unlocked_at if unlocked_record else None


class AquariumDetailSerializer(serializers.ModelSerializer):
    """개인 아쿠아리움 상세 정보"""
    svg_url = serializers.SerializerMethodField()
    background_name = serializers.CharField(source='background.background.name', read_only=True, default="기본 배경")
    fish_list = FishSerializer(source='fishes', many=True, read_only=True)

    class Meta:
        model = Aquarium
        fields = ['id', 'svg_url', 'background_name', 'fish_list']

    def get_svg_url(self, obj):
        if not obj.svg_path:
            return None
        request = self.context.get('request')
        timestamp = int(obj.updated_at.timestamp())
        full_path = f"{settings.MEDIA_URL}{obj.svg_path}?t={timestamp}"
        return request.build_absolute_uri(full_path) if request else full_path


class FishtankDetailSerializer(serializers.ModelSerializer):
    """레포지토리 수족관 상세 정보"""
    repository_full_name = serializers.CharField(source='repository.full_name', read_only=True)
    svg_url = serializers.SerializerMethodField()
    background_name = serializers.SerializerMethodField()
    fish_list = serializers.SerializerMethodField()

    class Meta:
        model = Fishtank
        fields = ['id', 'repository_full_name', 'svg_url', 'background_name', 'fish_list']

    def get_svg_url(self, obj):
        if not obj.svg_path:
            return None
        request = self.context.get('request')
        timestamp = int(obj.updated_at.timestamp())
        full_path = f"{settings.MEDIA_URL}{obj.svg_path}?t={timestamp}"
        return request.build_absolute_uri(full_path) if request else full_path

    def get_background_name(self, obj):
        if obj.background and obj.background.background:
            return obj.background.background.name
        return "기본 배경"

    @swagger_serializer_method(serializer_or_field=FishSerializer(many=True))
    def get_fish_list(self, obj):
        # 1. 물고기 목록 조회 (Related Join 최적화)
        fishes = ContributionFish.objects.filter(
            contributor__repository=obj.repository,
            is_visible_in_fishtank=True
        ).select_related('fish_species', 'contributor__repository', 'contributor__user')

        # 2. [N+1 최적화] 현재 유저의 도감 정보를 한 번에 조회하여 Map 생성
        request = self.context.get('request')
        unlocked_map = {}
        if request and request.user.is_authenticated:
            # {species_id: unlocked_at} 딕셔너리 생성
            unlocked_records = UnlockedFish.objects.filter(user=request.user).values('fish_species_id', 'unlocked_at')
            unlocked_map = {r['fish_species_id']: r['unlocked_at'] for r in unlocked_records}

        # 3. Serializer Context에 Map 전달
        context = self.context.copy()
        context['unlocked_map'] = unlocked_map

        return FishSerializer(fishes, many=True, context=context).data


class BackgroundChangeSerializer(serializers.Serializer):
    background_id = serializers.IntegerField(help_text="적용할 배경 ID")


class FishVisibilityItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    visible = serializers.BooleanField()


class FishVisibilityBulkUpdateSerializer(serializers.Serializer):
    fish_settings = FishVisibilityItemSerializer(many=True)


class OwnBackgroundListSerializer(serializers.ModelSerializer):
    background_id = serializers.IntegerField(source='background.id', read_only=True)
    name = serializers.CharField(source='background.name', read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = OwnBackground
        fields = ['background_id', 'name', 'image_url', 'unlocked_at']

    def get_image_url(self, obj):
        if obj.background.background_image:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.background.background_image.url) if request else obj.background.background_image.url
        return None


class UserFishListSerializer(serializers.ModelSerializer):
    species_name = serializers.CharField(source='fish_species.name', read_only=True)
    repository_full_name = serializers.CharField(source='contributor.repository.full_name', read_only=True)
    group_code = serializers.CharField(source='fish_species.group_code', read_only=True)
    maturity = serializers.IntegerField(source='fish_species.maturity', read_only=True)

    class Meta:
        model = ContributionFish
        fields = [
            'id', 'species_name', 'group_code', 'maturity', 
            'repository_full_name', 'is_visible_in_fishtank', 
            'is_visible_in_aquarium', 'aquarium'
        ]
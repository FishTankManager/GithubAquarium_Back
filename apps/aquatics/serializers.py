from rest_framework import serializers
from .models import Aquarium, Fishtank, ContributionFish, UnlockedFish, OwnBackground, FishtankSetting
from drf_yasg.utils import swagger_serializer_method

class FishSerializer(serializers.ModelSerializer):
    """아쿠아리움/피시탱크 내부 물고기 상세 정보"""
    name = serializers.CharField(source='fish_species.name', read_only=True, help_text="물고기 종 이름")
    group_code = serializers.CharField(source='fish_species.group_code', read_only=True, help_text="진화 그룹 코드")
    maturity = serializers.IntegerField(source='fish_species.maturity', read_only=True, help_text="성장 단계 (1~6)")
    repository_name = serializers.CharField(source='contributor.repository.full_name', read_only=True, help_text="출처 레포지토리 풀네임")
    commit_count = serializers.IntegerField(source='contributor.commit_count', read_only=True, help_text="해당 레포지토리에 기여한 커밋 수")
    unlocked_at = serializers.SerializerMethodField(help_text="해당 물고기 종을 해금한 시각 (Fishdex용)")

    class Meta:
        model = ContributionFish
        fields = [
            'id', 'name', 'group_code', 'maturity', 
            'repository_name', 'commit_count', 
            'unlocked_at', 'is_visible_in_aquarium', 'is_visible_in_fishtank'
        ]

    def get_unlocked_at(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if not user or not user.is_authenticated:
            return None
        unlocked_record = UnlockedFish.objects.filter(user=user, fish_species=obj.fish_species).first()
        return unlocked_record.unlocked_at if unlocked_record else None


class AquariumDetailSerializer(serializers.ModelSerializer):
    """개인 아쿠아리움 상세 정보"""
    background_name = serializers.CharField(source='background.background.name', read_only=True, help_text="적용된 배경 이름")
    fish_list = FishSerializer(source='fishes', many=True, read_only=True, help_text="아쿠아리움에 배치된 물고기 목록")

    class Meta:
        model = Aquarium
        fields = ['id', 'svg_path', 'background_name', 'fish_list']


class FishtankDetailSerializer(serializers.ModelSerializer):
    repository_full_name = serializers.CharField(source='repository.full_name', read_only=True, help_text="레포지토리 이름")
    background_name = serializers.SerializerMethodField(help_text="해당 유저가 설정한 수족관 배경 이름")
    
    # 이 부분에 FishSerializer를 사용한다고 명시해줍니다.
    fish_list = serializers.SerializerMethodField(help_text="수족관에 노출 설정된 모든 기여자의 물고기 목록")

    class Meta:
        model = Fishtank
        fields = ['id', 'repository_full_name', 'svg_path', 'background_name', 'fish_list']

    def get_background_name(self, obj):
        user = self.context.get('request').user
        setting = FishtankSetting.objects.filter(fishtank=obj, contributor=user).first()
        return setting.background.background.name if setting and setting.background else "기본 배경"

    # @swagger_serializer_method를 사용하여 Swagger에게 리턴 타입을 알려줍니다.
    @swagger_serializer_method(serializer_or_field=FishSerializer(many=True))
    def get_fish_list(self, obj):
        fishes = ContributionFish.objects.filter(
            contributor__repository=obj.repository,
            is_visible_in_fishtank=True
        ).select_related('fish_species', 'contributor__repository')
        # context를 전달해야 FishSerializer 내부의 get_unlocked_at이 정상 작동합니다.
        return FishSerializer(fishes, many=True, context=self.context).data


class BackgroundChangeSerializer(serializers.Serializer):
    background_id = serializers.IntegerField(help_text="적용할 배경(OwnBackground)의 ID")


class FishVisibilityItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text="기여 물고기(ContributionFish)의 고유 ID")
    visible = serializers.BooleanField(help_text="표시 여부 (true: 표시, false: 숨김)")


class FishVisibilityBulkUpdateSerializer(serializers.Serializer):
    fish_settings = FishVisibilityItemSerializer(many=True, help_text="물고기별 노출 설정 리스트")


class OwnBackgroundListSerializer(serializers.ModelSerializer):
    background_id = serializers.IntegerField(source='background.id', read_only=True, help_text="배경 원형 ID")
    name = serializers.CharField(source='background.name', read_only=True, help_text="배경 이름")
    image_url = serializers.ImageField(source='background.background_image', read_only=True, help_text="배경 이미지 URL")

    class Meta:
        model = OwnBackground
        fields = ['background_id', 'name', 'image_url', 'unlocked_at']


class UserFishListSerializer(serializers.ModelSerializer):
    species_name = serializers.CharField(source='fish_species.name', read_only=True, help_text="물고기 종 이름")
    repository_full_name = serializers.CharField(source='contributor.repository.full_name', read_only=True, help_text="출처 레포지토리 이름")

    class Meta:
        model = ContributionFish
        fields = [
            'id', 'species_name', 'repository_full_name', 
            'is_visible_in_fishtank', 'is_visible_in_aquarium', 'aquarium'
        ]
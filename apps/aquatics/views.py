from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema

from .models import Aquarium, Fishtank, OwnBackground, ContributionFish, FishtankSetting
from apps.repositories.models import Repository
from .serializers import (
    AquariumDetailSerializer, 
    FishtankDetailSerializer,
    BackgroundChangeSerializer,
    UserFishListSerializer,
    OwnBackgroundListSerializer,
    FishVisibilityBulkUpdateSerializer
)

# --- 개인 아쿠아리움 관련 ---

class AquariumDetailView(generics.RetrieveAPIView):
    """
    내 아쿠아리움 상세 조회 API
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AquariumDetailSerializer

    def get_object(self):
        aquarium, _ = Aquarium.objects.get_or_create(user=self.request.user)
        return aquarium

    @swagger_auto_schema(
        operation_summary="내 아쿠아리움 상세 조회",
        operation_description="현재 로그인한 사용자의 개인 아쿠아리움 정보와 배치된 물고기 목록을 가져옵니다.",
        responses={200: AquariumDetailSerializer()}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AquariumBackgroundUpdateView(APIView):
    """
    개인 아쿠아리움 배경 변경 API
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="내 아쿠아리움 배경 변경",
        operation_description="보유 중인 배경(OwnBackground) ID를 전달하여 아쿠아리움의 배경을 교체합니다.",
        request_body=BackgroundChangeSerializer,
        responses={200: "성공적으로 변경됨", 404: "보유하지 않은 배경 ID"}
    )
    def post(self, request):
        serializer = BackgroundChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        own_bg = get_object_or_404(OwnBackground, user=request.user, background_id=serializer.validated_data['background_id'])
        
        aquarium, _ = Aquarium.objects.get_or_create(user=request.user)
        aquarium.background = own_bg
        aquarium.save()
        return Response({"detail": "아쿠아리움 배경이 업데이트되었습니다."})


# --- 레포지토리 피시탱크 관련 ---

class FishtankDetailView(generics.RetrieveAPIView):
    """
    레포지토리 수족관 상세 조회 API
    """
    permission_classes = [IsAuthenticated]
    serializer_class = FishtankDetailSerializer

    def get_object(self):
        repo_id = self.kwargs.get('repo_id')
        repository = get_object_or_404(Repository, id=repo_id)
        fishtank, _ = Fishtank.objects.get_or_create(repository=repository)
        return fishtank

    @swagger_auto_schema(
        operation_summary="레포지토리 수족관 상세 조회",
        operation_description="특정 레포지토리에 속한 공용 수족관 정보를 가져옵니다. 모든 기여자의 공개된 물고기가 표시됩니다.",
        responses={200: FishtankDetailSerializer()}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class FishtankBackgroundUpdateView(APIView):
    """
    레포지토리 수족관 배경 설정 API (유저별 설정)
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="레포지토리 수족관 배경 설정",
        operation_description="특정 수족관을 볼 때 적용할 자신만의 배경을 설정합니다. (다른 유저에게는 영향을 주지 않습니다.)",
        request_body=BackgroundChangeSerializer,
        responses={200: "성공적으로 설정됨", 404: "레포지토리 또는 배경 정보 없음"}
    )
    def post(self, request, repo_id):
        serializer = BackgroundChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        own_bg = get_object_or_404(OwnBackground, user=request.user, background_id=serializer.validated_data['background_id'])
        repository = get_object_or_404(Repository, id=repo_id)
        fishtank, _ = Fishtank.objects.get_or_create(repository=repository)

        setting, _ = FishtankSetting.objects.get_or_create(fishtank=fishtank, contributor=request.user)
        setting.background = own_bg
        setting.save()

        return Response({"detail": "수족관 배경 설정이 업데이트되었습니다."})


class FishtankFishVisibilityUpdateView(APIView):
    """
    레포지토리 수족관 내 내 물고기 노출 설정 API
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="레포지토리 수족관 내 물고기 노출 설정",
        operation_description="해당 레포지토리 수족관에서 내 물고기를 다른 사람들에게 보여줄지 여부를 일괄 설정합니다.",
        request_body=FishVisibilityBulkUpdateSerializer,
        responses={200: "설정 완료", 400: "잘못된 물고기 ID 또는 권한 없음"}
    )
    def post(self, request, repo_id):
        serializer = FishVisibilityBulkUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        fish_settings = serializer.validated_data['fish_settings']
        fish_ids = [item['id'] for item in fish_settings]

        user_fishes = ContributionFish.objects.filter(
            id__in=fish_ids, 
            contributor__user=request.user,
            contributor__repository_id=repo_id
        )

        if user_fishes.count() != len(set(fish_ids)):
            return Response({"detail": "이 레포지토리에 대한 권한이 없는 물고기 ID가 포함되어 있습니다."}, status=400)

        settings_map = {item['id']: item['visible'] for item in fish_settings}

        with transaction.atomic():
            for fish in user_fishes:
                fish.is_visible_in_fishtank = settings_map[fish.id]
                fish.save()

        return Response({"detail": "수족관 물고기 노출 설정이 완료되었습니다."})


# --- 유저 인벤토리 관련 ---

class UserContributionFishListView(generics.ListAPIView):
    """
    내가 보유한 물고기 전체 목록 API
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserFishListSerializer

    def get_queryset(self):
        return ContributionFish.objects.filter(contributor__user=self.request.user).select_related('fish_species', 'contributor__repository')

    @swagger_auto_schema(
        operation_summary="내 전체 물고기 목록 조회",
        operation_description="모든 레포지토리 기여를 통해 획득한 내 물고기들의 전체 리스트를 가져옵니다.",
        responses={200: UserFishListSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class UserOwnBackgroundListView(generics.ListAPIView):
    """
    내가 보유한 배경 전체 목록 API
    """
    permission_classes = [IsAuthenticated]
    serializer_class = OwnBackgroundListSerializer

    def get_queryset(self):
        return OwnBackground.objects.filter(user=self.request.user).select_related('background')

    @swagger_auto_schema(
        operation_summary="내 보유 배경 목록 조회",
        operation_description="상점 구매 등으로 해금하여 아쿠아리움에 적용 가능한 배경 리스트를 가져옵니다.",
        responses={200: OwnBackgroundListSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AquariumFishVisibilityUpdateView(APIView):
    """
    개인 아쿠아리움 내 물고기 배치 설정 API
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="내 아쿠아리움 물고기 배치 설정",
        operation_description="개인 아쿠아리움에 어떤 물고기를 꺼내놓을지 일괄 설정합니다.",
        request_body=FishVisibilityBulkUpdateSerializer,
        responses={200: "배치 완료"}
    )
    def post(self, request):
        serializer = FishVisibilityBulkUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        fish_settings = serializer.validated_data['fish_settings']
        aquarium, _ = Aquarium.objects.get_or_create(user=request.user)
        
        fish_ids = [item['id'] for item in fish_settings]
        user_fishes = ContributionFish.objects.filter(id__in=fish_ids, contributor__user=request.user)

        settings_map = {item['id']: item['visible'] for item in fish_settings}

        with transaction.atomic():
            for fish in user_fishes:
                visible = settings_map[fish.id]
                fish.is_visible_in_aquarium = visible
                fish.aquarium = aquarium if visible else None
                fish.save()

        return Response({"detail": "아쿠아리움 물고기 배치가 완료되었습니다."})
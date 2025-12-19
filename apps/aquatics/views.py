from django.db import transaction
from django.shortcuts import get_object_or_404
from django_q.tasks import async_task  # 비동기 태스크 호출을 위해 추가
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from .models import Aquarium, Fishtank, OwnBackground, ContributionFish
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
    permission_classes = [IsAuthenticated]
    serializer_class = AquariumDetailSerializer

    def get_object(self):
        # [방안 B 반영] get_or_create 후 반환
        aquarium, _ = Aquarium.objects.get_or_create(user=self.request.user)
        return aquarium

    @swagger_auto_schema(
        operation_summary="내 아쿠아리움 상세 조회",
        responses={200: AquariumDetailSerializer()}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AquariumBackgroundUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="내 아쿠아리움 배경 변경",
        request_body=BackgroundChangeSerializer,
        responses={200: "성공적으로 변경됨"}
    )
    def post(self, request):
        serializer = BackgroundChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        own_bg = get_object_or_404(OwnBackground, user=request.user, background_id=serializer.validated_data['background_id'])
        aquarium, _ = Aquarium.objects.get_or_create(user=request.user)
        
        aquarium.background = own_bg
        aquarium.save()

        # 배경이 바뀌었으므로 아쿠아리움 SVG 재생성 예약
        async_task('apps.aquatics.tasks.generate_aquarium_svg_task', request.user.id)

        return Response({"detail": "아쿠아리움 배경이 업데이트되었습니다."})


# --- 레포지토리 피시탱크 관련 (개별 유저 뷰 기반) ---

class FishtankDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FishtankDetailSerializer

    def get_object(self):
        repo_id = self.kwargs.get('repo_id')
        repository = get_object_or_404(Repository, id=repo_id)
        # 이제 Fishtank는 (repository, user) 쌍으로 유일함
        fishtank, _ = Fishtank.objects.get_or_create(
            repository=repository, 
            user=self.request.user
        )
        return fishtank
    
    @swagger_auto_schema(
        operation_summary="레포지토리 수족관 상세 조회",
        manual_parameters=[
            openapi.Parameter('repo_id', openapi.IN_PATH, description="레포지토리의 DB ID", type=openapi.TYPE_INTEGER)
        ],
        responses={200: FishtankDetailSerializer()}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class FishtankBackgroundUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="레포지토리 수족관 배경 설정",
        operation_description="해당 수족관을 볼 때 적용할 '나만의' 배경을 설정합니다.",
        request_body=BackgroundChangeSerializer,
        responses={200: "성공적으로 설정됨"}
    )
    def post(self, request, repo_id):
        serializer = BackgroundChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        own_bg = get_object_or_404(OwnBackground, user=request.user, background_id=serializer.validated_data['background_id'])
        repository = get_object_or_404(Repository, id=repo_id)
        
        # 통합된 Fishtank 모델에서 직접 배경 수정
        fishtank, _ = Fishtank.objects.get_or_create(repository=repository, user=request.user)
        fishtank.background = own_bg
        fishtank.save()

        # 배경이 바뀌었으므로 이 유저의 해당 레포지토리 수족관 SVG 재생성 예약
        async_task('apps.aquatics.tasks.generate_fishtank_svg_task', repository.id, request.user.id)

        return Response({"detail": "수족관 배경 설정이 업데이트되었습니다."})


class FishtankFishVisibilityUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="레포지토리 수족관 내 내 물고기 노출 설정",
        request_body=FishVisibilityBulkUpdateSerializer,
        responses={200: "설정 완료"}
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
            return Response({"detail": "권한이 없는 물고기 ID가 포함되어 있습니다."}, status=status.HTTP_400_BAD_REQUEST)

        settings_map = {item['id']: item['visible'] for item in fish_settings}

        with transaction.atomic():
            for fish in user_fishes:
                fish.is_visible_in_fishtank = settings_map[fish.id]
                fish.save()

        # 내 물고기의 노출 여부가 바뀌면, 이 레포지토리를 구독(Fishtank 생성)한 
        # 모든 유저의 수족관 SVG에 내 물고기가 나타나거나 사라져야 함.
        # 성능을 위해 해당 레포지토리의 모든 Fishtank 뷰 갱신 예약
        related_fishtanks = Fishtank.objects.filter(repository_id=repo_id)
        for ft in related_fishtanks:
            async_task('apps.aquatics.tasks.generate_fishtank_svg_task', repo_id, ft.user_id)

        return Response({"detail": "수족관 물고기 노출 설정이 완료되었습니다."})


# --- 유저 인벤토리 및 기타 ---

class UserContributionFishListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserFishListSerializer

    def get_queryset(self):
        return ContributionFish.objects.filter(contributor__user=self.request.user).select_related('fish_species', 'contributor__repository')


class UserOwnBackgroundListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OwnBackgroundListSerializer

    def get_queryset(self):
        return OwnBackground.objects.filter(user=self.request.user).select_related('background')


class AquariumFishVisibilityUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="내 아쿠아리움 물고기 배치 설정",
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

        # 개인 아쿠아리움 배치 변경 후 SVG 재생성
        async_task('apps.aquatics.tasks.generate_aquarium_svg_task', request.user.id)

        return Response({"detail": "아쿠아리움 물고기 배치가 완료되었습니다."})
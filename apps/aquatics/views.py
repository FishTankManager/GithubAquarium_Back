# apps/aquatics/views.py
import os
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django_q.tasks import async_task

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
# 동기 생성을 위한 렌더러 직접 임포트
from apps.aquatics.renderers import render_aquarium_svg, render_fishtank_svg

# --- 개인 아쿠아리움 관련 ---

class AquariumDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AquariumDetailSerializer

    def get_object(self):
        user = self.request.user
        aquarium, created = Aquarium.objects.get_or_create(user=user)
        
        # [수정] SVG가 없거나 생성 직후라면 즉시 생성 (Lazy Generation)
        if not aquarium.svg_path:
            try:
                # 1. 렌더링
                svg_content = render_aquarium_svg(user)
                if svg_content:
                    # 2. 파일 저장
                    file_name = f"aquariums/aquarium_{user.id}.svg"
                    path = os.path.join(settings.MEDIA_ROOT, file_name)
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(svg_content)
                    
                    # 3. DB 업데이트
                    aquarium.svg_path = file_name
                    aquarium.save(update_fields=['svg_path'])
            except Exception as e:
                # 에러가 나더라도 객체는 반환 (이미지는 깨질 수 있음)
                print(f"Error generating Aquarium SVG sync: {e}")

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

        # 배경 변경 후 비동기 재생성
        async_task('apps.aquatics.tasks.generate_aquarium_svg_task', request.user.id)

        return Response({"detail": "아쿠아리움 배경이 업데이트되었습니다."})


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

        # 배치 변경 후 비동기 재생성
        async_task('apps.aquatics.tasks.generate_aquarium_svg_task', request.user.id)

        return Response({"detail": "아쿠아리움 물고기 배치가 완료되었습니다."})


# --- 레포지토리 피시탱크 관련 ---

class FishtankDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FishtankDetailSerializer

    def get_object(self):
        repo_id = self.kwargs.get('repo_id')
        repository = get_object_or_404(Repository, id=repo_id)
        user = self.request.user
        
        fishtank, created = Fishtank.objects.get_or_create(
            repository=repository, 
            user=user
        )

        # [수정] SVG가 없거나 생성 직후라면 즉시 생성 (Lazy Generation)
        if not fishtank.svg_path:
            try:
                svg_content = render_fishtank_svg(repository, user)
                if svg_content:
                    file_name = f"fishtanks/repo_{repository.id}_user_{user.id}.svg"
                    path = os.path.join(settings.MEDIA_ROOT, file_name)
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(svg_content)
                        
                    fishtank.svg_path = file_name
                    fishtank.save(update_fields=['svg_path'])
            except Exception as e:
                print(f"Error generating Fishtank SVG sync: {e}")

        return fishtank
    
    @swagger_auto_schema(
        operation_summary="레포지토리 수족관 상세 조회",
        manual_parameters=[
            openapi.Parameter('repo_id', openapi.IN_PATH, description="레포지토리 ID", type=openapi.TYPE_INTEGER)
        ],
        responses={200: FishtankDetailSerializer()}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class FishtankBackgroundUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="레포지토리 수족관 배경 설정",
        request_body=BackgroundChangeSerializer,
        responses={200: "성공적으로 설정됨"}
    )
    def post(self, request, repo_id):
        serializer = BackgroundChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        own_bg = get_object_or_404(OwnBackground, user=request.user, background_id=serializer.validated_data['background_id'])
        repository = get_object_or_404(Repository, id=repo_id)
        
        fishtank, _ = Fishtank.objects.get_or_create(repository=repository, user=request.user)
        fishtank.background = own_bg
        fishtank.save()

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

        # 전체 유저의 뷰 갱신 필요 (내 물고기가 사라졌으므로)
        related_fishtanks = Fishtank.objects.filter(repository_id=repo_id)
        for ft in related_fishtanks:
            async_task('apps.aquatics.tasks.generate_fishtank_svg_task', repo_id, ft.user_id)

        return Response({"detail": "수족관 물고기 노출 설정이 완료되었습니다."})


# --- 유저 인벤토리 ---

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
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
from django.http import HttpResponse #렌더
from .renderers import render_aquarium_svg , render_fishtank_svg #렌더

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
from apps.aquatics.renderers import render_aquarium_svg, render_fishtank_svg

import logging
logger = logging.getLogger(__name__)
# --- 개인 아쿠아리움 관련 ---

class AquariumDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AquariumDetailSerializer

    def get_object(self):
        user = self.request.user
        aquarium, _ = Aquarium.objects.get_or_create(user=user)
        if not aquarium.svg_path:
            try:
                svg_content = render_aquarium_svg(user)
                if svg_content:
                    file_name = f"aquariums/aquarium_{user.id}.svg"
                    path = os.path.join(settings.MEDIA_ROOT, file_name)
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(svg_content)
                    aquarium.svg_path = file_name
                    aquarium.save(update_fields=['svg_path'])
            except Exception as e:
                print(f"Error generating Aquarium SVG sync: {e}")
        return aquarium

    @swagger_auto_schema(
        operation_summary="내 아쿠아리움 상세 조회",
        operation_description="현재 사용자의 개인 아쿠아리움 정보와 렌더링된 SVG URL을 반환합니다.",
        tags=["Personal Aquarium"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class AquariumBackgroundUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="내 아쿠아리움 배경 변경",
        operation_description="보유 중인 배경 중 하나를 선택하여 개인 아쿠아리움에 적용합니다.",
        tags=["Personal Aquarium"],
        request_body=BackgroundChangeSerializer,
        responses={200: "성공적으로 변경됨", 404: "보유하지 않은 배경"}
    )
    def post(self, request):
        serializer = BackgroundChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        own_bg = get_object_or_404(OwnBackground, user=request.user, background_id=serializer.validated_data['background_id'])
        aquarium, _ = Aquarium.objects.get_or_create(user=request.user)
        aquarium.background = own_bg
        aquarium.save()
        async_task('apps.aquatics.tasks.generate_aquarium_svg_task', request.user.id)
        return Response({"detail": "아쿠아리움 배경이 업데이트되었습니다."})

class AquariumFishVisibilityUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="내 아쿠아리움 물고기 배치 설정",
        operation_description="개인 아쿠아리움에 노출할 물고기들을 벌크로 설정합니다.",
        tags=["Personal Aquarium"],
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
        async_task('apps.aquatics.tasks.generate_aquarium_svg_task', request.user.id)
        return Response({"detail": "아쿠아리움 물고기 배치가 완료되었습니다."})

class FishtankDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FishtankDetailSerializer

    def get_object(self):
        repo_id = self.kwargs.get('repo_id')
        repository = get_object_or_404(Repository, id=repo_id)
        fishtank, _ = Fishtank.objects.get_or_create(repository=repository, user=self.request.user)
        if not fishtank.svg_path:
            try:
                svg_content = render_fishtank_svg(repository, self.request.user)
                if svg_content:
                    file_name = f"fishtanks/repo_{repository.id}_user_{self.request.user.id}.svg"
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
        operation_description="특정 레포지토리의 공용 수족관 정보를 조회합니다. (유저별 커스텀 배경 반영)",
        tags=["Repository Fishtank"],
        manual_parameters=[openapi.Parameter('repo_id', openapi.IN_PATH, description="레포지토리 ID", type=openapi.TYPE_INTEGER)]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class FishtankBackgroundUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="레포지토리 수족관 배경 설정",
        operation_description="특정 레포지토리 수족관을 볼 때 사용할 내 배경을 설정합니다.",
        tags=["Repository Fishtank"],
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
        operation_description="공용 수족관에서 다른 유저들에게 내 물고기를 보여줄지 여부를 설정합니다.",
        tags=["Repository Fishtank"],
        request_body=FishVisibilityBulkUpdateSerializer,
        responses={200: "설정 완료", 400: "권한 없음"}
    )
    def post(self, request, repo_id):
        serializer = FishVisibilityBulkUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        fish_settings = serializer.validated_data['fish_settings']
        fish_ids = [item['id'] for item in fish_settings]
        user_fishes = ContributionFish.objects.filter(id__in=fish_ids, contributor__user=request.user, contributor__repository_id=repo_id)
        if user_fishes.count() != len(set(fish_ids)):
            return Response({"detail": "권한이 없는 물고기가 포함됨"}, status=400)
        settings_map = {item['id']: item['visible'] for item in fish_settings}
        with transaction.atomic():
            for fish in user_fishes:
                fish.is_visible_in_fishtank = settings_map[fish.id]
                fish.save()
        related_fishtanks = Fishtank.objects.filter(repository_id=repo_id)
        for ft in related_fishtanks:
            async_task('apps.aquatics.tasks.generate_fishtank_svg_task', repo_id, ft.user_id)
        return Response({"detail": "수족관 노출 설정 완료"})

class UserContributionFishListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserFishListSerializer

    @swagger_auto_schema(
        operation_summary="내 보유 물고기 목록 조회",
        operation_description="모든 레포지토리 기여를 통해 획득한 나의 모든 물고기 리스트를 조회합니다.",
        tags=["Inventory"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return ContributionFish.objects.filter(contributor__user=self.request.user).select_related('fish_species', 'contributor__repository')

class UserOwnBackgroundListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OwnBackgroundListSerializer

    @swagger_auto_schema(
        operation_summary="내 보유 배경 목록 조회",
        operation_description="상점 구매나 이벤트를 통해 해금한 나의 모든 배경 리스트를 조회합니다.",
        tags=["Inventory"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return OwnBackground.objects.filter(user=self.request.user).select_related('background')


class AquariumFishVisibilityUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="내 아쿠아리움 물고기 배치 설정",
        request_body=FishVisibilityBulkUpdateSerializer,
        responses={200: "배치 완료"},
        tags=["Personal Aquarium"],
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
    


# --- render 테스트용 뷰 ---
class AquariumSvgPreviewView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="(DEBUG) 내 아쿠아리움 SVG 프리뷰 (저장 없이 즉시 반환)",
        manual_parameters=[
            openapi.Parameter("as_text", openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN,
                              description="true면 JSON으로 svg 문자열 반환, false면 image/svg+xml로 반환", default=False),
        ],
        responses={200: "SVG or JSON"},
        tags=["SVG Preview"],
    )
    def get(self, request):
        
        svg = render_aquarium_svg(request.user)
        

        logger.warning(f"[PREVIEW] svg_type={type(svg)} svg_len={(len(svg) if svg else 0)}")

        if request.query_params.get("as_text") in ["1", "true", "True"]:
            return Response({"svg": svg})
        return HttpResponse(svg, content_type="image/svg+xml; charset=utf-8")


class FishtankSvgPreviewView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_summary="(DEBUG) 특정 repo의 피시탱크 SVG 프리뷰 (저장 없이 즉시 반환)",
        manual_parameters=[
            openapi.Parameter("as_text", openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN,
                              description="true면 JSON으로 svg 문자열 반환, false면 image/svg+xml로 반환", default=False),
        ],
        tags=["SVG Preview"],
        responses={200: "SVG or JSON"}
    )
    def get(self, request, repo_id: int):
        repo = Repository.objects.get(id=repo_id)
        svg = render_fishtank_svg(repo, request.user)
        if request.query_params.get("as_text") in ["1", "true", "True"]:
            return Response({"svg": svg})

        return HttpResponse(svg, content_type="image/svg+xml; charset=utf-8")
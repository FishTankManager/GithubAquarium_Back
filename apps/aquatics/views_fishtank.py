#aquatics/views_fishtank.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.http import HttpResponse
from apps.repositories.models import Repository
from apps.aquatics.models import Fishtank, FishtankSetting, OwnBackground,ContributionFish
from apps.aquatics.serializers_fishtank import (
    FishtankDetailSerializer,
    FishtankBackgroundSerializer,
)
from apps.aquatics.renderer.tank import render_aquarium_svg
from apps.aquatics.renderer.tank import render_fishtank_svg
# ----------------------------------------------------------
# 1) Fishtank 상세 조회
# ----------------------------------------------------------
class FishtankDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="피쉬탱크 상세 조회",
        operation_description="레포지토리 ID를 기반으로 피쉬탱크 내부 정보(기여자, 물고기)를 조회합니다.",
        responses={200: FishtankDetailSerializer}
    )
    def get(self, request, repo_id):
        try:
            repository = Repository.objects.get(id=repo_id)
            fishtank = repository.fishtank
        except Repository.DoesNotExist:
            return Response({"detail": "Repository not found"}, status=404)

        serializer = FishtankDetailSerializer(fishtank)
        return Response(serializer.data, status=200)


# ----------------------------------------------------------
# 2) Fishtank SVG
# ----------------------------------------------------------
class FishtankSVGView(APIView):

    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_summary="피쉬탱크 SVG 렌더링",
        operation_description="특정 Repository의 fishtank를 하나의 SVG로 렌더링합니다.",
        responses={200: "SVG XML String"},
    )
    def get(self, request, repo_id):
        try:
            repository = Repository.objects.get(id=repo_id)
        except Repository.DoesNotExist:
            return Response({"detail": "Repository not found"}, status=404)

        svg = render_fishtank_svg(repository)
        return HttpResponse(svg, content_type="image/svg+xml")

# ----------------------------------------------------------
# 3) 유저가 소유한 fishtank 배경 목록
# ----------------------------------------------------------
class FishtankBackgroundListView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="피쉬탱크 배경 목록 조회",
        operation_description="유저가 보유한 배경(OwnBackground)의 원본 Background 데이터를 반환합니다.",
        responses={200: FishtankBackgroundSerializer(many=True)}
    )
    def get(self, request):
        owned = OwnBackground.objects.filter(user=request.user)
        backgrounds = [ob.background for ob in owned]
        serializer = FishtankBackgroundSerializer(backgrounds, many=True)
        return Response(serializer.data, status=200)


# ----------------------------------------------------------
# 4) 피쉬탱크 배경 적용
# ----------------------------------------------------------
class ApplyFishtankBackgroundView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="피쉬탱크 배경 적용",
        operation_description="사용자가 소유한 OwnBackground 중 하나를 fishtank 배경으로 적용합니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "background_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="유저가 소유한 OwnBackground.background.id"
                ),
            },
            required=["background_id"]
        ),
        responses={
            200: openapi.Response("Background applied"),
            400: "Bad Request",
            404: "Not Found",
        },
    )

    def post(self, request, repo_id):
        bg_id = request.data.get("background_id")

        try:
            repository = Repository.objects.get(id=repo_id)
            fishtank = repository.fishtank
        except Repository.DoesNotExist:
            return Response({"detail": "Repository not found"}, status=404)

        try:
            owned_bg = OwnBackground.objects.get(
                user=request.user, background_id=bg_id
            )
        except OwnBackground.DoesNotExist:
            return Response({"detail": "Background not owned"}, status=400)

        setting, _ = FishtankSetting.objects.update_or_create(
            fishtank=fishtank,
            contributor=request.user,
            defaults={"background": owned_bg},
        )

        return Response({"detail": "Background applied"}, status=200)


# ----------------------------------------------------------
# 5) Fishtank Export (scale, offset 저장)
# ----------------------------------------------------------
'''
class FishtankExportView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="피쉬탱크 Export (scale/offset 저장)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "scale": openapi.Schema(type=openapi.TYPE_NUMBER),
                "offset_x": openapi.Schema(type=openapi.TYPE_NUMBER),
                "offset_y": openapi.Schema(type=openapi.TYPE_NUMBER),
            },
            required=["scale"]
        ),
        responses={200: "Saved"}
    )

    def post(self, request, repo_id):

        # 저장 필드가 모델에 아직 없기 때문에, 저장 로직은 후에 추가 가능
        return Response({"detail": "Saved"}, status=200)
'''    
# 9) 피쉬탱크 선택 가능한 물고기 목록
class FishtankSelectableFishView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="특정 Repository의 Fishtank 물고기 목록 조회",
        operation_description=(
            "repository_id에 해당하는 Fishtank에서 기여자 기반으로 생성된 "
            "ContributionFish 목록을 반환합니다.\n\n"
            "각 객체는 물고기의 식별자(id), 기여자 username, "
            "물고기 species 이름, commit_count, 그리고 사용자가 현재 FishTank에 "
            "표시되도록 선택했는지 여부(selected)를 포함합니다."
        ),
        manual_parameters=[
            openapi.Parameter(
                'repo_id',
                openapi.IN_PATH,
                description="Repository ID",
                type=openapi.TYPE_INTEGER,
                required=True,
            )
        ],
        responses={
            200: openapi.Response(
                description="물고기 목록 반환",
                examples={
                    "application/json": {
                        "fishes": [
                            {
                                "id": 12,
                                "username": "alice",
                                "species": "Salmon",
                                "commit_count": 34,
                                "selected": True
                            },
                            {
                                "id": 13,
                                "username": "bob",
                                "species": "Goldfish",
                                "commit_count": 12,
                                "selected": False
                            }
                        ]
                    }
                }
            ),
            404: openapi.Response(
                description="Fishtank not found",
                examples={
                    "application/json": {"detail": "Fishtank not found"}
                }
            )
        }
    )
    def get(self, request, repo_id):
        try:
            fishtank = Fishtank.objects.get(repository_id=repo_id)
        except Fishtank.DoesNotExist:
            return Response({"detail": "Fishtank not found"}, status=404)

        fishes = ContributionFish.objects.filter(
            contributor__repository_id=repo_id
        ).select_related("fish_species", "contributor__user")

        data = []
        for f in fishes:
            data.append({
                "id": f.id,
                "username": f.contributor.user.username,
                "species": f.fish_species.name,
                "commit_count": f.contributor.commit_count,
                "selected": f.is_visible_in_fishtank,
            })

        return Response({"fishes": data}, status=200)
# 10) 피쉬탱크 Export → 선택 상태 실제 저장
class FishtankExportSelectionView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="피쉬탱크 Export - 선택된 물고기 적용",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "fish_ids": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_INTEGER)
                )
            },
            required=["fish_ids"]
        ),
        responses={200: "Saved"}
    )
    def post(self, request, repo_id):
        selected_ids = request.data.get("fish_ids", [])

        try:
            Fishtank.objects.get(repository_id=repo_id)
        except Fishtank.DoesNotExist:
            return Response({"detail": "Fishtank not found"}, status=404)

        fishes = ContributionFish.objects.filter(
            contributor__repository_id=repo_id
        )

        # 1) 선택되지 않은 물고기 → 숨김
        fishes.exclude(id__in=selected_ids).update(is_visible_in_fishtank=False)

        # 2) 선택된 물고기 → 표시
        fishes.filter(id__in=selected_ids).update(is_visible_in_fishtank=True)

        return Response({"detail": "Fishtank updated"}, status=200)

class FishtankSpriteListView(APIView):
    """
    특정 레포지토리의 fishtank를 프론트 FishTankTest / FishSpriteTest로 그리기 위한 데이터.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="피쉬탱크용 스프라이트 리스트",
        operation_description=(
            "repo_id에 해당하는 Fishtank에서 표시 상태(is_visible_in_fishtank=True)인 "
            "물고기들의 스프라이트 SVG와 라벨을 반환합니다."
        ),
        responses={200: "background_url + fishes 배열"}
    )
    def get(self, request, repo_id):
        try:
            repository = Repository.objects.get(id=repo_id)
            fishtank = repository.fishtank
        except Repository.DoesNotExist:
            return Response({"detail": "Repository not found"}, status=404)
        except Fishtank.DoesNotExist:
            return Response({"detail": "Fishtank not found"}, status=404)

        # 피쉬탱크 배경: FishtankSetting 에서 현재 유저가 설정한 배경 1개만 쓴다고 가정
        setting = fishtank.settings.select_related("background__background").filter(
            contributor=request.user
        ).first()

        if setting and setting.background and setting.background.background.background_image:
            bg_url = setting.background.background.background_image.url
        else:
            bg_url = ""

        fishes = (
            ContributionFish.objects
            .filter(contributor__repository=repository, is_visible_in_fishtank=True)
            .select_related("fish_species", "contributor__user")
        )

        fish_list = []
        for cf in fishes:
            label_text = cf.contributor.user.username  # 혹은 repository.name 등

            fish_list.append({
                "id": cf.id,
                "label": label_text,
                "svg_source": cf.fish_species.svg_template,
            })

        return Response({
            "background_url": bg_url,
            "fishes": fish_list,
        }, status=200)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
#fishtank views.py

from apps.repositories.models import Repository
from apps.aquatics.models import Fishtank, FishtankSetting, OwnBackground
from apps.aquatics.serializers_fishtank import (
    FishtankDetailSerializer,
    FishtankBackgroundSerializer,
)
#from apps.aquatics.renderer.tank import render_aquarium_svg

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
        operation_description="유저 기반 SVG 렌더링을 반환합니다.",
        responses={200: "SVG XML String"}
    )

    def get(self, request, repo_id):
        try:
            Repository.objects.get(id=repo_id)
        except Repository.DoesNotExist:
            return Response({"detail": "Repository not found"}, status=404)

        svg = render_aquarium_svg(request.user)
        return Response(svg, content_type="image/svg+xml")


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
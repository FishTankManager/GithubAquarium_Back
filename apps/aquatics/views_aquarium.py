from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.aquatics.models import Aquarium, ContributionFish, OwnBackground
from apps.aquatics.serializers_aquarium import (
    AquariumDetailSerializer,
    AquariumFishSerializer,
    AquariumBackgroundSerializer,
)
from apps.aquatics.renderer.tank import render_aquarium_svg


# ----------------------------------------------------------
# 1) 아쿠아리움 전체 조회
# ----------------------------------------------------------
class AquariumDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="아쿠아리움 상세 조회",
        responses={200: AquariumDetailSerializer()}
    )
    def get(self, request):
        aquarium = request.user.aquarium
        fishes = ContributionFish.objects.filter(aquarium=aquarium)

        serializer = AquariumDetailSerializer(
            aquarium, context={"fishes": fishes}
        )
        serializer._data["fishes"] = AquariumFishSerializer(fishes, many=True).data
        return Response(serializer.data, status=200)


# ----------------------------------------------------------
# 2) 내가 가진 물고기 전체 조회 (언락된 모든 물고기)
# ----------------------------------------------------------
class MyUnlockedFishListView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="유저가 언락한 모든 물고기 조회",
        responses={200: AquariumFishSerializer(many=True)}
    )
    def get(self, request):
        fishes = ContributionFish.objects.filter(
            contributor__user=request.user
        )
        data = AquariumFishSerializer(fishes, many=True).data
        return Response(data, status=200)


# ----------------------------------------------------------
# 3) 아쿠아리움에 물고기 추가
# ----------------------------------------------------------
class AquariumAddFishView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="아쿠아리움에 물고기 추가",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "contribution_fish_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="ContributionFish ID"
                )
            },
            required=["contribution_fish_id"]
        ),
        responses={200: "Added"}
    )
    def post(self, request):
        cf_id = request.data.get("contribution_fish_id")
        aquarium = request.user.aquarium

        try:
            cf = ContributionFish.objects.get(id=cf_id)
        except ContributionFish.DoesNotExist:
            return Response({"detail": "Fish not found"}, status=404)

        cf.aquarium = aquarium
        cf.save()
        return Response({"detail": "Added to aquarium"}, status=200)


# ----------------------------------------------------------
# 4) 아쿠아리움 물고기 제거
# ----------------------------------------------------------
class AquariumRemoveFishView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="아쿠아리움 물고기 제거",
        responses={200: "Removed"}
    )
    def delete(self, request, fish_id):
        try:
            cf = ContributionFish.objects.get(id=fish_id, aquarium=request.user.aquarium)
        except ContributionFish.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)

        cf.aquarium = None
        cf.save()
        return Response({"detail": "Removed"}, status=200)


# ----------------------------------------------------------
# 5) 아쿠아리움 배경 목록 조회
# ----------------------------------------------------------
class AquariumBackgroundListView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="아쿠아리움 배경 목록 조회",
        responses={200: AquariumBackgroundSerializer(many=True)}
    )
    def get(self, request):
        owned = OwnBackground.objects.filter(user=request.user)
        data = AquariumBackgroundSerializer(owned, many=True).data
        return Response(data, status=200)


# ----------------------------------------------------------
# 6) 아쿠아리움 배경 적용
# ----------------------------------------------------------
class AquariumApplyBackgroundView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="아쿠아리움 배경 적용",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={"own_background_id": openapi.Schema(type=openapi.TYPE_INTEGER)},
            required=["own_background_id"]
        ),
        responses={200: "Applied"}
    )
    def post(self, request):
        bg_id = request.data.get("own_background_id")

        try:
            bg = OwnBackground.objects.get(id=bg_id, user=request.user)
        except OwnBackground.DoesNotExist:
            return Response({"detail": "Background not owned"}, status=400)

        aquarium = request.user.aquarium
        aquarium.background = bg
        aquarium.save()

        return Response({"detail": "Background applied"}, status=200)


# ----------------------------------------------------------
# 7) Export 저장 (scale/offset)
# ----------------------------------------------------------
class AquariumExportView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="아쿠아리움 Export 저장",
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
    def post(self, request):
        # 모델 확장 시 여기에 저장 로직 추가
        return Response({"detail": "Saved"}, status=200)


# ----------------------------------------------------------
# 8) SVG 렌더링
# ----------------------------------------------------------
class AquariumSVGView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="아쿠아리움 SVG 렌더링",
        responses={200: "SVG XML"}
    )
    def get(self, request):
        svg = render_aquarium_svg(request.user)
        return Response(svg, content_type="image/svg+xml")

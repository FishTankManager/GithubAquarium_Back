#aquatics/views_aquarium.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.http import HttpResponse
from apps.aquatics.models import ContributionFish, OwnBackground
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
'''
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
'''

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
        return HttpResponse(svg, content_type="image/svg+xml")


# 9) 아쿠아리움 선택 가능한 물고기 목록
class AquariumSelectableFishView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="선택 가능한 물고기 목록 조회",
        operation_description="유저가 보유한 모든 ContributionFish를 selectable 형태로 반환합니다.",
        responses={200: "Selectable fish list"}
    )
    def get(self, request):
        user = request.user
        aquarium = user.aquarium

        fishes = ContributionFish.objects.filter(contributor__user=user) \
            .select_related("fish_species", "contributor__repository")

        data = []
        for f in fishes:
            is_in_aquarium = (f.aquarium_id == aquarium.id)
            data.append({
                "id": f.id,
                "species": f.fish_species.name,
                "repo_name": f.contributor.repository.name,
                "selected": is_in_aquarium and f.is_visible_in_aquarium
            })

        return Response({"fishes": data}, status=200)
# 10) Export: 프론트 선택 상태를 실제 DB에 반영
class AquariumExportSelectionView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="아쿠아리움 Export - 선택된 물고기 저장",
        operation_description="프론트에서 최종 선택된 물고기 ID 목록을 받아 DB에 반영합니다.",
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
    def post(self, request):
        user = request.user
        aquarium = user.aquarium
        selected_ids = request.data.get("fish_ids", [])

        # 1) 유저가 소유한 모든 fish 가져오기
        all_my_fish = ContributionFish.objects.filter(contributor__user=user)

        # 2) 선택되지 않은 물고기 → aquarium에서 제거
        all_my_fish.exclude(id__in=selected_ids).update(aquarium=None)
        
        # 3) 선택된 물고기 → aquarium에 추가하고 보이게 설정
        all_my_fish.filter(id__in=selected_ids).update(aquarium=aquarium, is_visible_in_aquarium=True)

        return Response({"detail": "Aquarium updated"}, status=200)


class AquariumSpriteListView(APIView):
    """
    프론트 FishTankTest + FishSpriteTest에 맞는 데이터 포맷:
    - background_url: 현재 아쿠아리움 배경 이미지
    - fishes: [{ id, label, svg_source }, ...]
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="아쿠아리움용 스프라이트 리스트",
        operation_description=(
            "프론트에서 FishTankTest / FishSpriteTest로 바로 사용할 수 있도록 "
            "배경 이미지와 각 물고기의 스프라이트 SVG를 반환합니다."
        ),
        responses={200: "background_url + fishes 배열"}
    )
    def get(self, request):
        user = request.user
        aquarium: Aquarium = user.aquarium

        # 배경 URL
        if aquarium.background and aquarium.background.background.background_image:
            bg_url = aquarium.background.background.background_image.url
        else:
            bg_url = ""

        # 이 유저 아쿠아리움에 들어있는 물고기들
        fishes = (
            ContributionFish.objects
            .filter(aquarium=aquarium, is_visible_in_aquarium=True)
            .select_related("fish_species", "contributor__repository", "contributor__user")
        )

        fish_list = []
        for cf in fishes:
            # 프론트에서 label 로 쓸 텍스트 (원하는 쪽 골라서 사용)
            # 예시 1: 레포지토리 이름
            # label_text = cf.contributor.repository.name
            # 예시 2: 기여자 username
            label_text = cf.contributor.user.username

            fish_list.append({
                "id": cf.id,
                "label": label_text,
                "svg_source": cf.fish_species.svg_template,
            })

        return Response({
            "background_url": bg_url,
            "fishes": fish_list,
        }, status=200)
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import random
import logging

from .models import Item, UserCurrency, UserInventory, PointLog
from .serializers import (
    ShopItemSerializer, 
    UserCurrencySerializer, 
    UserInventorySerializer,
    PurchaseRequestSerializer
)
from apps.aquatics.models import OwnBackground, ContributionFish
from apps.items.models import FishSpecies
from django_q.tasks import async_task

logger = logging.getLogger(__name__)

class ShopItemListView(generics.ListAPIView):
    """
    상점에서 판매 중인 아이템 목록을 조회합니다.
    """
    permission_classes = [AllowAny]
    serializer_class = ShopItemSerializer
    
    def get_queryset(self):
        return Item.objects.filter(is_active=True).order_by('price')

class MyShopInfoView(APIView):
    """
    내 재화(포인트) 잔액과 보유 중인 소모성 아이템(인벤토리)을 조회합니다.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="내 지갑 및 인벤토리 조회",
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'currency': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'inventory': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT))
                }
            )
        }
    )
    def get(self, request):
        currency, _ = UserCurrency.objects.get_or_create(user=request.user)
        inventory = UserInventory.objects.filter(user=request.user, quantity__gt=0)
        
        return Response({
            'currency': UserCurrencySerializer(currency).data,
            'inventory': UserInventorySerializer(inventory, many=True).data
        })

class PurchaseItemView(APIView):
    """
    아이템 구매 뷰
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="아이템 구매",
        request_body=PurchaseRequestSerializer,
        responses={200: "구매 성공", 400: "잔액 부족 등"}
    )
    def post(self, request):
        serializer = PurchaseRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item_id = serializer.validated_data['item_id']
        user = request.user

        item = get_object_or_404(Item, id=item_id, is_active=True)
        currency_pre, _ = UserCurrency.objects.get_or_create(user=user)

        try:
            with transaction.atomic():
                currency = UserCurrency.objects.select_for_update().get(id=currency_pre.id)

                if currency.balance < item.price:
                    return Response({"detail": "잔액이 부족합니다."}, status=status.HTTP_400_BAD_REQUEST)

                if item.item_type == Item.ItemType.BG_UNLOCK:
                    if OwnBackground.objects.filter(user=user, background=item.target_background).exists():
                        return Response({"detail": "이미 보유한 배경입니다."}, status=status.HTTP_400_BAD_REQUEST)
                    OwnBackground.objects.create(user=user, background=item.target_background)
                    purchase_desc = f"배경 구매: {item.target_background.name}"
                else:
                    inventory, _ = UserInventory.objects.get_or_create(user=user, item=item)
                    inventory.quantity += 1
                    inventory.save()
                    purchase_desc = f"아이템 구매: {item.name}"

                currency.balance -= item.price
                currency.save()

                PointLog.objects.create(
                    user=user, amount=-item.price,
                    reason=PointLog.Reason.SHOP_PURCHASE, description=purchase_desc
                )
                return Response({"detail": "구매가 완료되었습니다.", "balance": currency.balance})
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UseRerollTicketView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="리롤권 사용 (그룹 랜덤 변경)",
        operation_description="""
        리롤권 1개를 사용하여 특정 레포지토리의 내 물고기를 다시 뽑습니다.
        - **로직:** 새로운 물고기 그룹(group_code)을 랜덤으로 선택합니다.
        - 그 후, 해당 그룹 내에서 사용자의 **현재 커밋 수에 맞는 가장 높은 단계(Maturity)**의 물고기로 자동 결정됩니다.
        - 성공 시 아쿠아리움 및 수족관 SVG가 즉시 재생성 예약됩니다.
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "repo_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="리롤할 대상 레포지토리 ID")
            },
            required=["repo_id"]
        ),
        responses={
            200: "리롤 성공",
            400: "아이템 부족 등",
            404: "물고기 없음"
        }
    )
    def post(self, request):
        repo_id = request.data.get("repo_id")
        user = request.user

        if not repo_id:
            return Response({"detail": "repo_id가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # 1. 리롤권 확인 (Lock)
                inventory_item = UserInventory.objects.select_for_update().filter(
                    user=user, 
                    item__item_type=Item.ItemType.REROLL_TICKET, 
                    quantity__gt=0
                ).first()

                if not inventory_item:
                    return Response({"detail": "리롤권이 부족합니다."}, status=status.HTTP_400_BAD_REQUEST)

                # 2. 대상 물고기 및 기여자 정보 조회
                try:
                    target_fish = ContributionFish.objects.select_related('contributor').select_for_update().get(
                        contributor__user=user,
                        contributor__repository_id=repo_id
                    )
                except ContributionFish.DoesNotExist:
                    return Response({"detail": "해당 레포지토리에 보유한 물고기가 없습니다."}, status=status.HTTP_404_NOT_FOUND)

                contributor = target_fish.contributor
                current_species = target_fish.fish_species

                # 3. 새로운 그룹 코드 결정
                # 전체 그룹 코드 중 현재 그룹을 제외하고 랜덤 선택
                all_groups = list(FishSpecies.objects.values_list('group_code', flat=True).distinct())
                other_groups = [g for g in all_groups if g != current_species.group_code]
                
                # 다른 그룹이 없다면 (종류가 하나뿐이면) 현재 그룹 내에서라도 다시 결정
                new_group_code = random.choice(other_groups) if other_groups else current_species.group_code

                # 4. 새 그룹 내에서 기여자의 커밋 수에 맞는 물고기 종 찾기
                # 커밋 수(required_commits)를 만족하는 가장 높은 단계(maturity) 선택
                new_species = FishSpecies.objects.filter(
                    group_code=new_group_code,
                    required_commits__lte=contributor.commit_count
                ).order_by('-maturity').first()

                # 혹시라도 조건에 맞는 게 없으면(커밋 0 등) 해당 그룹의 1단계 할당
                if not new_species:
                    new_species = FishSpecies.objects.filter(group_code=new_group_code).order_by('maturity').first()

                if not new_species:
                    return Response({"detail": "새로운 물고기 종을 결정할 수 없습니다."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                # 5. 데이터 업데이트
                target_fish.fish_species = new_species
                target_fish.save()

                inventory_item.quantity -= 1
                inventory_item.save()

                PointLog.objects.create(
                    user=user, amount=0,
                    reason=PointLog.Reason.ITEM_USE,
                    description=f"리롤권 사용: {current_species.group_code} -> {new_species.group_code} (Lv.{new_species.maturity})"
                )

            # 6. [중요] 트랜잭션 종료 후 SVG 재생성 태스크 호출
            # 개인 아쿠아리움 갱신
            async_task('apps.aquatics.tasks.generate_aquarium_svg_task', user.id)
            # 해당 레포지토리의 피시탱크 갱신 (리롤한 유저의 뷰 갱신)
            async_task('apps.aquatics.tasks.generate_fishtank_svg_task', repo_id, user.id)

            return Response({
                "detail": "물고기 그룹이 성공적으로 변경되었습니다.",
                "old_species": f"{current_species.name} (Lv.{current_species.maturity})",
                "new_species": f"{new_species.name} (Lv.{new_species.maturity})",
                "remaining_tickets": inventory_item.quantity
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in UseRerollTicketView: {e}", exc_info=True)
            return Response({"detail": "처리 중 오류가 발생했습니다."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
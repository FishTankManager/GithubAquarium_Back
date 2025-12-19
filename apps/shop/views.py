from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import random

from .models import Item, UserCurrency, UserInventory, PointLog
from .serializers import (
    ShopItemSerializer, 
    UserCurrencySerializer, 
    UserInventorySerializer,
    PurchaseRequestSerializer
)
from apps.aquatics.models import OwnBackground
from apps.items.models import FishSpecies
from apps.aquatics.models import ContributionFish

class ShopItemListView(generics.ListAPIView):
    """
    상점에서 판매 중인 아이템 목록을 조회합니다.
    로그인한 경우 'is_owned' 필드를 통해 배경 보유 여부를 알 수 있습니다.
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
                    'currency': openapi.Schema(type=openapi.TYPE_OBJECT, description="UserCurrencySerializer 구조"),
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
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="아이템 구매",
        operation_description="""
        포인트를 사용하여 아이템을 구매합니다.
        - 배경 해금권(BG_UNLOCK): 즉시 OwnBackground 생성 (재구매 불가)
        - 소모품(REROLL 등): UserInventory 수량 증가
        """,
        request_body=PurchaseRequestSerializer,
        responses={
            200: "구매 성공",
            400: "잘못된 요청 (이미 보유중, 잔액 부족 등)",
            404: "아이템 없음"
        }
    )
    def post(self, request):
        serializer = PurchaseRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item_id = serializer.validated_data['item_id']
        user = request.user

        item = get_object_or_404(Item, id=item_id, is_active=True)

        # [방안 B] 트랜잭션 외부에서 먼저 레코드를 확보하여 Race Condition 방지
        currency_pre, _ = UserCurrency.objects.get_or_create(user=user)

        try:
            with transaction.atomic():
                currency = UserCurrency.objects.select_for_update().get(id=currency_pre.id)

                if currency.balance < item.price:
                    return Response(
                        {"detail": "잔액이 부족합니다.", "current_balance": currency.balance}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # 4. 아이템 타입별 처리
                if item.item_type == Item.ItemType.BG_UNLOCK:
                    # 배경 해금권: 이미 가지고 있는지 확인
                    if not item.target_background:
                        return Response({"detail": "설정 오류: 대상 배경이 없는 아이템입니다."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                    if OwnBackground.objects.filter(user=user, background=item.target_background).exists():
                        return Response({"detail": "이미 보유한 배경입니다."}, status=status.HTTP_400_BAD_REQUEST)
                    
                    # 배경 지급
                    OwnBackground.objects.create(user=user, background=item.target_background)
                    purchase_desc = f"배경 구매: {item.target_background.name}"

                elif item.item_type == Item.ItemType.REROLL_TICKET: # ItemType Choice 확인 필요 (models.py에 REROLL로 정의됨)
                    # 소모품: 인벤토리 추가
                    inventory, created = UserInventory.objects.get_or_create(user=user, item=item)
                    inventory.quantity += 1
                    inventory.save()
                    purchase_desc = f"아이템 구매: {item.name}"
                
                else:
                    # 기타 아이템 (현재는 REROLL과 동일하게 처리하거나 에러)
                    inventory, created = UserInventory.objects.get_or_create(user=user, item=item)
                    inventory.quantity += 1
                    inventory.save()
                    purchase_desc = f"아이템 구매: {item.name}"

                # 5. 비용 차감 및 저장
                currency.balance -= item.price
                currency.save()

                # 6. 로그 기록
                PointLog.objects.create(
                    user=user,
                    amount=-item.price,
                    reason=PointLog.Reason.SHOP_PURCHASE,
                    description=purchase_desc
                )
                
                return Response({
                    "detail": "구매가 완료되었습니다.",
                    "item": item.name,
                    "balance": currency.balance
                }, status=status.HTTP_200_OK)

        except Exception as e:
            # 예기치 못한 에러
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UseRerollTicketView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="리롤권 사용 (물고기 변경)",
        operation_description="""
        소모품(REROLL_TICKET) 1개를 사용하여 특정 레포지토리의 내 물고기를 다시 뽑습니다.
        - 현재 물고기와 동일한 성장 단계(Maturity)의 다른 물고기 중 하나로 랜덤 변경됩니다.
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "repo_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="리롤할 대상 레포지토리 ID")
            },
            required=["repo_id"]
        ),
        responses={
            200: "리롤 성공 (변경된 물고기 정보 반환)",
            400: "아이템 부족 또는 잘못된 요청",
            404: "해당 레포지토리에 물고기가 없음"
        }
    )
    def post(self, request):
        repo_id = request.data.get("repo_id")
        user = request.user

        if not repo_id:
            return Response({"detail": "repo_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # 1. 인벤토리에서 리롤권 확인 및 차감 (Lock 사용)
                # Item의 code가 'TICKET_REROLL' 이거나 item_type이 'REROLL'인 아이템을 찾습니다.
                # 여기서는 item_type='REROLL' 인 아이템 중 하나를 쓴다고 가정 (보통 1종류)
                inventory_item = UserInventory.objects.select_for_update().filter(
                    user=user, 
                    item__item_type=Item.ItemType.REROLL_TICKET, 
                    quantity__gt=0
                ).first()

                if not inventory_item:
                    return Response({"detail": "리롤권이 부족합니다."}, status=status.HTTP_400_BAD_REQUEST)

                # 2. 대상 물고기 조회
                try:
                    target_fish = ContributionFish.objects.select_for_update().get(
                        contributor__user=user,
                        contributor__repository_id=repo_id
                    )
                except ContributionFish.DoesNotExist:
                    return Response({"detail": "해당 레포지토리에 보유한 물고기가 없습니다."}, status=status.HTTP_404_NOT_FOUND)

                # 3. 새로운 물고기 종 선정 로직
                current_species = target_fish.fish_species
                current_maturity = current_species.maturity
                
                # 같은 maturity를 가진 모든 물고기 후보군 조회
                candidates = list(FishSpecies.objects.filter(maturity=current_maturity))
                
                # 후보가 2개 이상이라면 현재 물고기는 제외하고 랜덤 선택 (다양성 보장)
                if len(candidates) > 1:
                    candidates = [f for f in candidates if f.id != current_species.id]
                
                # 만약 후보가 없다면(유일한 종이라면) 그대로 유지될 수도 있음 (혹은 에러 처리)
                if not candidates:
                     return Response({"detail": "교체 가능한 다른 물고기 종이 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

                new_species = random.choice(candidates)

                # 4. 데이터 업데이트
                # 4-1. 물고기 종 변경
                target_fish.fish_species = new_species
                target_fish.save()

                # 4-2. 아이템 차감
                inventory_item.quantity -= 1
                inventory_item.save()

                # 4-3. 로그 기록 (선택 사항, PointLog는 재화용이므로 별도 로그가 없으면 생략 가능하나 PointLog를 Item Use 용도로도 쓴다면 기록)
                PointLog.objects.create(
                    user=user,
                    amount=0, # 포인트 변동 없음
                    reason=PointLog.Reason.ITEM_USE, # models.py에 ITEM_USE 추가 필요하거나 없으면 기타 처리
                    description=f"리롤권 사용: {current_species.name} -> {new_species.name}"
                )

                return Response({
                    "detail": "물고기가 변경되었습니다.",
                    "old_species": current_species.name,
                    "new_species": new_species.name,
                    "remaining_tickets": inventory_item.quantity
                }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
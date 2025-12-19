# apps/shop/views.py
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
from django_q.tasks import async_task

from .models import Item, UserCurrency, UserInventory, PointLog
from .serializers import (
    ShopItemSerializer, 
    UserCurrencySerializer, 
    UserInventorySerializer,
    PurchaseRequestSerializer,
    RerollRequestSerializer  # 추가된 Serializer
)
from apps.aquatics.models import OwnBackground, ContributionFish
from apps.items.models import FishSpecies

logger = logging.getLogger(__name__)

class ShopItemListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ShopItemSerializer
    
    @swagger_auto_schema(
        operation_summary="상점 아이템 목록 조회",
        operation_description="판매 중인 모든 아이템(배경 해금권, 리롤권 등)을 조회합니다.",
        tags=["Shop"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return Item.objects.filter(is_active=True).order_by('price')

class MyShopInfoView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="내 지갑 및 소모품 인벤토리 조회",
        operation_description="보유 포인트 잔액과 리롤권 같은 소모성 아이템의 수량을 확인합니다.",
        tags=["Shop"],
        responses={200: "잔액 및 아이템 목록"}
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
        operation_description="포인트를 사용하여 배경 해금권이나 리롤권을 구매합니다.",
        tags=["Shop"],
        request_body=PurchaseRequestSerializer,
        responses={200: "구매 성공", 400: "잔액 부족 또는 이미 보유함"}
    )
    def post(self, request):
        serializer = PurchaseRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = get_object_or_404(Item, id=serializer.validated_data['item_id'], is_active=True)
        currency_pre, _ = UserCurrency.objects.get_or_create(user=request.user)
        with transaction.atomic():
            currency = UserCurrency.objects.select_for_update().get(id=currency_pre.id)
            if currency.balance < item.price:
                return Response({"detail": "잔액 부족"}, status=400)
            if item.item_type == Item.ItemType.BG_UNLOCK:
                if OwnBackground.objects.filter(user=request.user, background=item.target_background).exists():
                    return Response({"detail": "이미 보유함"}, status=400)
                OwnBackground.objects.create(user=request.user, background=item.target_background)
            else:
                inv, _ = UserInventory.objects.get_or_create(user=request.user, item=item)
                inv.quantity += 1
                inv.save()
            currency.balance -= item.price
            currency.save()
            PointLog.objects.create(user=request.user, amount=-item.price, reason=PointLog.Reason.SHOP_PURCHASE, description=f"구매: {item.name}")
        return Response({"detail": "구매 완료", "balance": currency.balance})

class UseRerollTicketView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="리롤권 사용 (물고기 종 변경)",
        operation_description="리롤권 1개를 사용하여 지정한 물고기(fish_id)의 패밀리(Group)를 랜덤하게 교체합니다. SVG가 즉시 갱신됩니다.",
        tags=["Shop"],
        request_body=RerollRequestSerializer,
        responses={
            200: "리롤 성공", 
            400: "리롤권 부족",
            404: "물고기를 찾을 수 없거나 권한 없음"
        }
    )
    def post(self, request):
        serializer = RerollRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        fish_id = serializer.validated_data['fish_id']
        user = request.user
        
        try:
            with transaction.atomic():
                # 1. 리롤권 보유 여부 확인 및 Lock
                inventory_item = UserInventory.objects.select_for_update().filter(
                    user=user, item__item_type=Item.ItemType.REROLL_TICKET, quantity__gt=0
                ).first()
                
                if not inventory_item:
                    return Response({"detail": "리롤권 부족"}, status=400)
                
                # 2. 대상 물고기 조회 (소유자 확인 포함)
                # repository 정보도 함께 로딩하여 나중에 ID 참조
                try:
                    target_fish = ContributionFish.objects.select_related(
                        'contributor', 'contributor__repository', 'fish_species'
                    ).select_for_update().get(
                        id=fish_id, 
                        contributor__user=user
                    )
                except ContributionFish.DoesNotExist:
                    return Response({"detail": "해당 물고기를 찾을 수 없습니다."}, status=404)

                # 3. 새로운 종(Group) 결정 로직
                current_group = target_fish.fish_species.group_code
                all_groups = list(FishSpecies.objects.values_list('group_code', flat=True).distinct())
                other_groups = [g for g in all_groups if g != current_group]
                
                # 다른 그룹 중 하나 랜덤 선택 (없으면 유지)
                new_group = random.choice(other_groups) if other_groups else current_group
                
                # 현재 커밋 수에 맞는 해당 그룹의 FishSpecies 조회
                commit_count = target_fish.contributor.commit_count
                new_species = FishSpecies.objects.filter(
                    group_code=new_group, 
                    required_commits__lte=commit_count
                ).order_by('-maturity').first()
                
                # 조건에 맞는게 없으면(커밋 부족 등) 1단계 강제 할당
                if not new_species:
                    new_species = FishSpecies.objects.filter(group_code=new_group).order_by('maturity').first()
                
                if not new_species:
                    raise Exception(f"FishSpecies data missing for group {new_group}")

                # 4. 저장 및 차감
                target_fish.fish_species = new_species
                target_fish.save()
                
                inventory_item.quantity -= 1
                inventory_item.save()

                # Task에 전달할 Repo ID 추출
                repo_id = target_fish.contributor.repository.id

            # 5. 비동기 SVG 갱신
            async_task('apps.aquatics.tasks.generate_aquarium_svg_task', user.id)
            async_task('apps.aquatics.tasks.generate_fishtank_svg_task', repo_id, user.id)
            
            return Response({
                "detail": "리롤 성공", 
                "new_species": new_species.name,
                "new_group": new_species.group_code
            })
            
        except Exception as e:
            logger.error(f"Error processing reroll: {e}", exc_info=True)
            return Response({"detail": "오류 발생"}, status=500)
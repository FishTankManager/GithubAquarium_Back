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
    PurchaseRequestSerializer
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
        operation_summary="리롤권 사용 (물고기 그룹 변경)",
        operation_description="리롤권 1개를 사용하여 특정 레포지토리의 물고기 패밀리를 랜덤하게 교체합니다. 교체 후 SVG가 즉시 갱신됩니다.",
        tags=["Shop"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={"repo_id": openapi.Schema(type=openapi.TYPE_INTEGER)},
            required=["repo_id"]
        ),
        responses={200: "리롤 성공", 400: "리롤권 부족"}
    )
    def post(self, request):
        repo_id = request.data.get("repo_id")
        user = request.user
        try:
            with transaction.atomic():
                inventory_item = UserInventory.objects.select_for_update().filter(
                    user=user, item__item_type=Item.ItemType.REROLL_TICKET, quantity__gt=0
                ).first()
                if not inventory_item:
                    return Response({"detail": "리롤권 부족"}, status=400)
                target_fish = ContributionFish.objects.select_related('contributor').select_for_update().get(
                    contributor__user=user, contributor__repository_id=repo_id
                )
                all_groups = list(FishSpecies.objects.values_list('group_code', flat=True).distinct())
                other_groups = [g for g in all_groups if g != target_fish.fish_species.group_code]
                new_group = random.choice(other_groups) if other_groups else target_fish.fish_species.group_code
                new_species = FishSpecies.objects.filter(group_code=new_group, required_commits__lte=target_fish.contributor.commit_count).order_by('-maturity').first()
                if not new_species:
                    new_species = FishSpecies.objects.filter(group_code=new_group).order_by('maturity').first()
                target_fish.fish_species = new_species
                target_fish.save()
                inventory_item.quantity -= 1
                inventory_item.save()
            async_task('apps.aquatics.tasks.generate_aquarium_svg_task', user.id)
            async_task('apps.aquatics.tasks.generate_fishtank_svg_task', repo_id, user.id)
            return Response({"detail": "리롤 성공", "new_species": new_species.name})
        except Exception as e:
            return Response({"detail": "오류 발생"}, status=500)
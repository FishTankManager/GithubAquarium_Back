# apps/shop/serializers.py
from rest_framework import serializers
from .models import Item, UserCurrency, UserInventory
from apps.aquatics.models import OwnBackground

class ShopItemSerializer(serializers.ModelSerializer):
    """상점 판매 아이템 정보"""
    target_background_name = serializers.CharField(source='target_background.name', read_only=True)
    is_owned = serializers.SerializerMethodField()

    class Meta:
        model = Item
        fields = [
            'id', 'code', 'name', 'description', 
            'item_type', 'price', 'image', 
            'target_background', 'target_background_name',
            'is_owned'
        ]

    def get_is_owned(self, obj):
        """
        배경 해금권의 경우, 유저가 이미 해당 배경을 가지고 있는지 확인.
        소모품(리롤권)은 소유 개념이 없으므로(여러 개 가질 수 있음) False 처리.
        """
        user = self.context.get('request').user
        if not user.is_authenticated:
            return False
            
        if obj.item_type == Item.ItemType.BG_UNLOCK and obj.target_background:
            return OwnBackground.objects.filter(
                user=user, 
                background=obj.target_background
            ).exists()
        return False

class UserCurrencySerializer(serializers.ModelSerializer):
    """유저 재화 정보"""
    class Meta:
        model = UserCurrency
        fields = ['balance', 'total_earned']

class UserInventorySerializer(serializers.ModelSerializer):
    """보유 아이템 정보"""
    item_name = serializers.CharField(source='item.name', read_only=True)
    item_code = serializers.CharField(source='item.code', read_only=True)
    item_image = serializers.ImageField(source='item.image', read_only=True)
    item_type = serializers.CharField(source='item.item_type', read_only=True)

    class Meta:
        model = UserInventory
        fields = ['item', 'item_code', 'item_name', 'item_type', 'quantity', 'item_image']

class PurchaseRequestSerializer(serializers.Serializer):
    """구매 요청 바디 검증"""
    item_id = serializers.IntegerField()

class PurchaseResponseSerializer(serializers.Serializer):
    """구매 결과 응답"""
    detail = serializers.CharField()
    balance = serializers.IntegerField()

class RerollRequestSerializer(serializers.Serializer):
    """리롤 요청 바디 검증 (repo_id 대신 fish_id 사용)"""
    fish_id = serializers.IntegerField(help_text="리롤할 대상 물고기(ContributionFish)의 고유 ID")
from django.urls import path
from .views import (
    ShopItemListView, 
    MyShopInfoView, 
    PurchaseItemView,
    UseRerollTicketView,
)

urlpatterns = [
    # 상점 목록 (로그인 안해도 볼 수는 있게 설정 가능)
    path('items/', ShopItemListView.as_view(), name='shop-item-list'),
    
    # 내 정보 (잔액, 인벤토리)
    path('my-info/', MyShopInfoView.as_view(), name='shop-my-info'),
    
    # 구매
    path('purchase/', PurchaseItemView.as_view(), name='shop-purchase'),

    # 리롤권 사용 엔드포인트 추가
    path('use-reroll/', UseRerollTicketView.as_view(), name='shop-use-reroll'),
]
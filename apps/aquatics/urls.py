from django.urls import path
from .views import (
    AquariumDetailView, 
    AquariumBackgroundUpdateView,
    AquariumFishVisibilityUpdateView,
    FishtankDetailView,
    FishtankBackgroundUpdateView,
    FishtankFishVisibilityUpdateView,
    UserContributionFishListView,
    UserOwnBackgroundListView,
)

urlpatterns = [
    # --- 개인 아쿠아리움 관리 ---
    path('aquarium/', AquariumDetailView.as_view(), name='aquarium-detail'),
    path('aquarium/background/', AquariumBackgroundUpdateView.as_view(), name='aquarium-bg-update'),
    path('aquarium/fishes/visibility/', AquariumFishVisibilityUpdateView.as_view(), name='aquarium-fish-visibility'),
    
    # --- 레포지토리 공용 수족관(피시탱크) 관리 ---
    path('fishtank/<int:repo_id>/', FishtankDetailView.as_view(), name='fishtank-detail'),
    path('fishtank/<int:repo_id>/background/', FishtankBackgroundUpdateView.as_view(), name='fishtank-bg-update'),
    path('fishtank/<int:repo_id>/fishes/visibility/', FishtankFishVisibilityUpdateView.as_view(), name='fishtank-fish-visibility'),

    # --- 유저 인벤토리(보유 자산) 조회 ---
    path('my-fishes/', UserContributionFishListView.as_view(), name='user-fish-list'),
    path('my-backgrounds/', UserOwnBackgroundListView.as_view(), name='user-backgrounds-list'),
]
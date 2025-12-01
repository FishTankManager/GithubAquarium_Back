from django.urls import path
from .views import AquariumSVGView
from .views_fishtank import (
    FishtankDetailView,
    FishtankSVGView,
    FishtankBackgroundListView,
    ApplyFishtankBackgroundView,
    FishtankExportView,
    FishtankSelectableFishView,
    FishtankExportSelectionView,
    FishtankSpriteListView,
)
from .views_aquarium import *

urlpatterns = [
    path("fishtank/<int:repo_id>/", FishtankDetailView.as_view()),
    path("fishtank/<int:repo_id>/svg/", FishtankSVGView.as_view()),
    path("fishtank/backgrounds/", FishtankBackgroundListView.as_view()),
    path("fishtank/<int:repo_id>/apply-background/", ApplyFishtankBackgroundView.as_view()),
    path("fishtank/<int:repo_id>/export/", FishtankExportView.as_view()),
    path("fishtank/<int:repo_id>/selectable-fish/", FishtankSelectableFishView.as_view()),
    path("fishtank/<int:repo_id>/export-selection/", FishtankExportSelectionView.as_view()),
    path("fishtank/<int:repo_id>/sprites/", FishtankSpriteListView.as_view(), name="fishtank-sprites"),

    path("aquarium/", AquariumDetailView.as_view()),
    path("aquarium/my-fishes/", MyUnlockedFishListView.as_view()),
    #path("aquarium/add-fish/", AquariumAddFishView.as_view()),
    #path("aquarium/remove-fish/<int:fish_id>/", AquariumRemoveFishView.as_view()),
    path("aquarium/backgrounds/", AquariumBackgroundListView.as_view()),
    path("aquarium/apply-background/", AquariumApplyBackgroundView.as_view()),
    path("aquarium/export/", AquariumExportView.as_view()),
    path("aquarium/svg/", AquariumSVGView.as_view()),
    path("aquarium/sprites/", AquariumSpriteListView.as_view(), name="aquarium-sprites"),
    path("aquarium/selectable-fish/", AquariumSelectableFishView.as_view()),
    path("aquarium/export-selection/", AquariumExportSelectionView.as_view()),
]

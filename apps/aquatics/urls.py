from django.urls import path
from .views_fishtank import (
    FishtankDetailView,
    FishtankSVGView,
    FishtankBackgroundListView,
    ApplyFishtankBackgroundView,
    FishtankExportView,
)

urlpatterns = [
    path("fishtank/<int:repo_id>/", FishtankDetailView.as_view()),
    path("fishtank/<int:repo_id>/svg/", FishtankSVGView.as_view()),
    path("fishtank/backgrounds/", FishtankBackgroundListView.as_view()),
    path("fishtank/<int:repo_id>/apply-background/", ApplyFishtankBackgroundView.as_view()),
    path("fishtank/<int:repo_id>/export/", FishtankExportView.as_view()),
]

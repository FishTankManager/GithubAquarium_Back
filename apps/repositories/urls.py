from django.urls import path
from .views import SyncRepositoriesView

urlpatterns = [
    # POST /api/repositories/sync/ 요청을 SyncRepositoriesView와 연결
    path('sync/', SyncRepositoriesView.as_view(), name='sync-repositories'),
]
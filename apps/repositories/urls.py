from django.urls import path
from .views import MyContributedRepositoryListView

urlpatterns = [
    path('', MyContributedRepositoryListView.as_view(), name='my-repository-list'),
]
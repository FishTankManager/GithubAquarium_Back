from django.urls import path
from .views import RepositoryListView
app_name = 'repositories'

urlpatterns = [
    path("", RepositoryListView.as_view(), name="repository-list"),
]

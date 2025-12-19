# apps/repositories/views.py
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Repository
from .serializers import RepositoryListSerializer
from drf_yasg.utils import swagger_auto_schema

class MyContributedRepositoryListView(generics.ListAPIView):
    serializer_class = RepositoryListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Repository.objects.filter(
            contributors__user=user,
            contributors__commit_count__gt=0
        ).select_related('owner') \
         .prefetch_related('contributors') \
         .distinct() \
         .order_by('-updated_at')

    @swagger_auto_schema(
        operation_summary="참여 중인 레포지토리 목록 조회",
        operation_description="사용자가 한 번이라도 커밋을 남긴 레포지토리 목록과 각 레포지토리별 내 커밋 수를 반환합니다.",
        tags=["Repositories"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
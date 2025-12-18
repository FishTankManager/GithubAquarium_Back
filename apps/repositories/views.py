from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Repository
from .serializers import RepositoryListSerializer
from drf_yasg.utils import swagger_auto_schema

class MyContributedRepositoryListView(generics.ListAPIView):
    """
    내가 단 1개 이상의 커밋이라도 남긴 모든 레포지토리 목록을 조회합니다.
    - 본인이 소유자(Owner)인지 여부와 상관없이 기여도가 있으면 반환합니다.
    """
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
        operation_description="커밋 기여 내역이 존재하는 모든 레포지토리를 내 기여도 정보와 함께 반환합니다.",
        responses={200: RepositoryListSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
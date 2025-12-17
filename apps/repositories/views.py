from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from drf_yasg.utils import swagger_auto_schema

from apps.repositories.models import Repository
from apps.repositories.serializers import RepositorySerializer


class RepositoryListView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="내가 커밋한 모든 레포지토리 리스트",
        operation_description=(
            "Contributor 테이블에서 commit_count > 0 인 repo만 반환합니다.\n"
            "즉, 내가 owner인지 상관없이 단 1커밋이라도 있는 모든 repo를 조회합니다."
        ),
        responses={200: RepositorySerializer(many=True)},
    )
    def get(self, request):
        try:
            user = request.user

            # user가 contributor 이고 commit_count > 0 인 repo만 조회
            contributed_repos = Repository.objects.filter(
                contributors__user=user,
                contributors__commit_count__gt=0
            ).distinct().order_by("-updated_at")

            serializer = RepositorySerializer(contributed_repos, many=True)
            return Response(serializer.data, status=200)
        except Exception as e:
            # 로깅은 Django의 기본 로깅 시스템을 사용
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error fetching repositories for user {request.user.id}: {str(e)}", exc_info=True)
            return Response(
                {"detail": "레포지토리 목록을 불러오는 중 오류가 발생했습니다."},
                status=500
            )

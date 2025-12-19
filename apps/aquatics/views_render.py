# apps/aquatics/views_render.py
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from apps.aquatics.renderers import render_aquarium_svg
from apps.repositories.models import Repository
from apps.aquatics.renderers import render_fishtank_svg

User = get_user_model()


class PublicAquariumSvgRenderView(APIView):
    """
    GitHub README용 Aquarium SVG 렌더
    - 로그인 필요 없음
    - SVG 직접 반환
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request, username: str):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return HttpResponse(
                "<svg xmlns='http://www.w3.org/2000/svg'></svg>",
                content_type="image/svg+xml",
                status=404,
            )

        width = int(request.GET.get("width", 700))
        height = int(request.GET.get("height", 400))

        svg = render_aquarium_svg(user, width=width, height=height)

        return HttpResponse(
            svg,
            content_type="image/svg+xml; charset=utf-8",
        )
    
class PublicFishtankSvgRenderView(APIView):
    """
    GitHub README용 Fishtank SVG 렌더
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request, username: str, repo_id: int):
        try:
            user = User.objects.get(username=username)
            repo = Repository.objects.get(id=repo_id)
        except (User.DoesNotExist, Repository.DoesNotExist):
            return HttpResponse(
                "<svg xmlns='http://www.w3.org/2000/svg'></svg>",
                content_type="image/svg+xml",
                status=404,
            )

        width = int(request.GET.get("width", 700))
        height = int(request.GET.get("height", 400))

        svg = render_fishtank_svg(repo, user, width=width, height=height)

        return HttpResponse(
            svg,
            content_type="image/svg+xml; charset=utf-8",
        )
    

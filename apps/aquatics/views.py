from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .renderer.tank import render_aquarium_svg

class AquariumSVGView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        svg = render_aquarium_svg(request.user)
        return Response(svg, content_type="image/svg+xml")

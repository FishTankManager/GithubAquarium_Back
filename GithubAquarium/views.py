# GithubAquarium/views.py
from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from django.conf import settings
from rest_framework.permissions import AllowAny 
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class GitHubLogin(SocialLoginView):
    """
    GitHub OAuth2를 이용한 소셜 로그인/회원가입을 처리합니다.
    """
    adapter_class = GitHubOAuth2Adapter
    callback_url = settings.GITHUB_CALLBACK_URL
    client_class = OAuth2Client
    permission_classes = (AllowAny,)
    authentication_classes = []

    @swagger_auto_schema(
        operation_summary="GitHub 소셜 로그인",
        operation_description="GitHub에서 받은 access_token을 전달하여 JWT 토큰을 발급받습니다.",
        tags=["Authentication"],
        responses={
            200: openapi.Response(
                description="로그인 성공. access 및 refresh 토큰이 쿠키 또는 바디로 반환됩니다.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'access': openapi.Schema(type=openapi.TYPE_STRING),
                        'refresh': openapi.Schema(type=openapi.TYPE_STRING),
                        'user': openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                            'pk': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'username': openapi.Schema(type=openapi.TYPE_STRING),
                        })
                    }
                )
            )
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
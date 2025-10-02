# GithubAquarium/urls.py

from django.contrib import admin
from django.urls import path, include
from .views import GitHubLogin

from dj_rest_auth.views import LogoutView, UserDetailsView
from dj_rest_auth.jwt_auth import get_refresh_view
from rest_framework_simplejwt.views import TokenVerifyView
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
   openapi.Info(
      title="GithubAquarium API",
      default_version='v1',
      description="GithubAquarium 프로젝트의 API 문서입니다.",
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # 0. Swagger (API 문서)
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    # 1. Django 관리자 페이지
    path('admin/', admin.site.urls),

    # 2. dj-rest-auth 인증 관련 URL
    #    - GitHub 소셜 로그인 시작
    path('dj-rest-auth/github/', GitHubLogin.as_view(), name='github_login'),
    #    - 로그아웃
    path('dj-rest-auth/logout/', LogoutView.as_view(), name='rest_logout'),
    #    - 현재 사용자 정보 조회
    path('dj-rest-auth/user/', UserDetailsView.as_view(), name='rest_user_details'),
    #    - JWT 토큰 검증 및 재발급
    path('dj-rest-auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('dj-rest-auth/token/refresh/', get_refresh_view().as_view(), name='token_refresh'),

    # 3. 로컬 앱 API URL
    path('repositories/', include('apps.repositories.urls')),
    # path('users/', include('apps.users.urls')),
]
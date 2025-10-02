# GithubAquarium/urls.py

from django.contrib import admin
from django.urls import path, include
from GithubAquarium.views import GitHubLogin

urlpatterns = [
    # 1. Django 관리자 페이지
    path('admin/', admin.site.urls),

    # 2. dj-rest-auth 인증 관련 URL
    #    - /dj-rest-auth/github/ : GitHub 소셜 로그인 시작
    #    - /dj-rest-auth/logout/ : 로그아웃
    #    - /dj-rest-auth/user/ : 현재 사용자 정보 조회
    path('dj-rest-auth/', include('dj_rest_auth.urls')),
    path('dj-rest-auth/github/', GitHubLogin.as_view(), name='github_login'),

    # 3. 로컬 앱 API URL
    path('repositories/', include('apps.repositories.urls')),
    # path('users/', include('apps.users.urls')),
]
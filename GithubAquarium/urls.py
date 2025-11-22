# GithubAquarium/urls.py
"""
Main URL configuration for the GithubAquarium project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/stable/topics/http/urls/
"""

from django.contrib import admin
from django.urls import path, include
from .views import GitHubLogin
from .webhook_views import GitHubWebhookView
from django.conf import settings
from django.conf.urls.static import static

from dj_rest_auth.views import LogoutView, UserDetailsView
from dj_rest_auth.jwt_auth import get_refresh_view
from rest_framework_simplejwt.views import TokenVerifyView
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# --- API Documentation (Swagger/drf-yasg) ---
# Setup for generating API documentation
schema_view = get_schema_view(
   openapi.Info(
      title="GithubAquarium API",
      default_version='v1',
      description="GithubAquarium 프로젝트의 API 문서입니다.",
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
   url='https://githubaquarium.store',
)

urlpatterns = [
    # --- API Docs ---
    # URLs for Swagger and ReDoc API documentation
    path('api/swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('api/swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    # --- Django Admin ---
    # URL for the Django admin interface
    path('api/admin/', admin.site.urls),

    # --- Authentication (dj-rest-auth) ---
    # URLs for handling user authentication and social login
    path('api/dj-rest-auth/github/', GitHubLogin.as_view(), name='github_login'),
    path('api/dj-rest-auth/logout/', LogoutView.as_view(), name='rest_logout'),
    path('api/dj-rest-auth/user/', UserDetailsView.as_view(), name='rest_user_details'),
    path('api/dj-rest-auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/dj-rest-auth/token/refresh/', get_refresh_view().as_view(), name='token_refresh'),

    # --- Webhooks ---
    # URL endpoint for receiving GitHub webhooks
    path('api/webhooks/github/', GitHubWebhookView.as_view(), name='github_webhook'),

    # --- Local App APIs ---
    # Include URL configurations from the 'repositories' and 'users' apps
    path('api/repositories/', include('apps.repositories.urls')),
    path('api/users/', include('apps.users.urls')),
    path('api/aquatics/', include('apps.aquatics.urls')),
    
    # --- DRF Auth ---
    path('api-auth/', include('rest_framework.urls')),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from django.conf import settings
from rest_framework.permissions import AllowAny 

class GitHubLogin(SocialLoginView):
    """
    Custom view for handling GitHub social login.

    This view integrates with django-allauth and dj-rest-auth to perform
    social authentication using a GitHub account. It specifies the adapter,
    callback URL, and client class necessary for the OAuth2 flow.
    """
    adapter_class = GitHubOAuth2Adapter
    callback_url = settings.GITHUB_CALLBACK_URL
    client_class = OAuth2Client
    # [추가] 이 뷰는 로그인 전이므로 누구나 접근 가능해야 함
    permission_classes = (AllowAny,)
    authentication_classes = []

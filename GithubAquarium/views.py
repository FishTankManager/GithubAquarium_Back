# GithubAquarium/views.py
"""
Core views for the GithubAquarium project.
"""

from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from django.conf import settings

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
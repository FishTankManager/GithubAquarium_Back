# apps/users/adapter.py
"""
Custom adapter for django-allauth to handle post-login logic.
"""
import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.shortcuts import get_current_site
from django.db import transaction  # 트랜잭션 관리 추가
from django_q.tasks import async_task
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialApp
from github import Github


# Standard instance of a logger
logger = logging.getLogger(__name__)
User = get_user_model()

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Overrides the default social account adapter to sync GitHub data upon user login.
    """

    def get_app(self, request, provider):
        """
        부모 클래스의 get_app을 호출하지 않고 직접 DB를 조회하거나 settings에서 생성합니다.
        """
        # 1. DB에서 해당 provider의 앱이 있는지 먼저 확인
        apps = SocialApp.objects.filter(provider=provider)
        
        if apps.exists():
            current_site = get_current_site(request)
            app = apps.filter(sites=current_site).first()
            if app:
                return app
            return apps.first()

        # 2. DB에 없으면 settings.py 설정값을 읽어와서 'DB에 새로 생성'
        logger.info(f"SocialApp for '{provider}' not found in DB. Creating from settings.")
        
        providers_setting = getattr(settings, 'SOCIALACCOUNT_PROVIDERS', {})
        provider_config = providers_setting.get(provider, {})
        app_config = provider_config.get('APP', {})
        
        client_id = app_config.get('client_id')
        secret = app_config.get('secret')

        if client_id and secret:
            app, created = SocialApp.objects.get_or_create(
                provider=provider,
                defaults={
                    'name': f"{provider}-auto-config",
                    'client_id': client_id,
                    'secret': secret,
                    'key': app_config.get('key', ''),
                }
            )
            current_site = get_current_site(request)
            app.sites.add(current_site)
            return app

        raise SocialApp.DoesNotExist(f"No SocialApp found for provider '{provider}'")

    def pre_social_login(self, request, sociallogin):
        """
        로그인 저장 직전, 토큰에 DB에 저장된 앱 객체를 연결합니다.
        """
        app = self.get_app(request, sociallogin.account.provider)
        sociallogin.token.app = app
        
        current_site = get_current_site(request)
        if not app.sites.filter(id=current_site.id).exists():
            app.sites.add(current_site)

        super().pre_social_login(request, sociallogin)

    def save_user(self, request, sociallogin, form=None):
        """
        사용자 저장 후 비동기 동기화 Task 호출
        """
        # 1. 사용자 기본 정보 저장 (필수)
        user = super().save_user(request, sociallogin, form)
        
        try:
            # 2. GitHub Access Token 확보
            access_token = sociallogin.token.token
            
            if not access_token:
                logger.warning("GitHub access token not found for user %s.", user.username)
                return user

            # 3. 사용자 기본 GitHub 정보 즉시 업데이트
            g = Github(access_token)
            github_user = g.get_user()
            
            user.github_id = github_user.id
            user.github_username = github_user.login
            user.avatar_url = github_user.avatar_url
            user.save()

            # 4. Task Queue에 작업 등록 (트랜잭션 커밋 후 실행 보장)
            # 이렇게 해야 Worker가 DB에서 user를 찾을 때 DoesNotExist 에러가 발생하지 않음
            transaction.on_commit(lambda: async_task(
                'apps.users.tasks.sync_github_data_task', # 실행할 함수 경로
                user.id,                                    # 인자 1: 유저 ID
                access_token,                               # 인자 2: 토큰
                task_name=f'sync_user_{user.id}'            # 작업 이름
            ))
            
            logger.info(f"Queued async sync task for user {user.username} (on commit)")

        except Exception as e:
            logger.error("Error scheduling GitHub sync for user %s: %s", user.username, e, exc_info=True)
            
        return user
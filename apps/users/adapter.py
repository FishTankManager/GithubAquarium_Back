"""
Custom adapter for django-allauth to handle post-login logic.
"""
import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.shortcuts import get_current_site
from django.db import transaction
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialApp
from github import Github, GithubException

from apps.repositories.models import Repository, Contributor, Commit

# Standard instance of a logger
logger = logging.getLogger(__name__)
User = get_user_model()

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Overrides the default social account adapter to sync GitHub data upon user login.
    """

    def get_app(self, request, provider):
        """
        [수정됨] 부모 클래스의 get_app을 호출하지 않고 직접 DB를 조회합니다.
        allauth가 settings.py 기반으로 만드는 '저장되지 않은 인스턴스'를 피하기 위함입니다.
        """
        # 1. DB에서 해당 provider의 앱이 있는지 먼저 확인
        apps = SocialApp.objects.filter(provider=provider)
        
        if apps.exists():
            # 앱이 여러 개라면 현재 사이트와 연결된 것을 우선적으로 찾음
            current_site = get_current_site(request)
            app = apps.filter(sites=current_site).first()
            if app:
                return app
            # 연결된 게 없으면 그냥 첫 번째 앱 반환
            return apps.first()

        # 2. DB에 없으면 settings.py 설정값을 읽어와서 'DB에 새로 생성'
        logger.info(f"SocialApp for '{provider}' not found in DB. Creating from settings.")
        
        providers_setting = getattr(settings, 'SOCIALACCOUNT_PROVIDERS', {})
        provider_config = providers_setting.get(provider, {})
        app_config = provider_config.get('APP', {})
        
        client_id = app_config.get('client_id')
        secret = app_config.get('secret')

        if client_id and secret:
            # update_or_create 대신 get_or_create 사용 (중복 방지)
            app, created = SocialApp.objects.get_or_create(
                provider=provider,
                defaults={
                    'name': f"{provider}-auto-config",
                    'client_id': client_id,
                    'secret': secret,
                    'key': app_config.get('key', ''),
                }
            )
            # 생성된 앱은 반드시 저장된 상태이므로 ID가 존재함
            
            # 현재 사이트와 연결
            current_site = get_current_site(request)
            app.sites.add(current_site)
            return app

        # 설정조차 없으면 에러 발생 (이 경우는 거의 없음)
        raise SocialApp.DoesNotExist(f"No SocialApp found for provider '{provider}'")

    def pre_social_login(self, request, sociallogin):
        """
        로그인 저장 직전, 토큰에 DB에 저장된 앱 객체를 연결합니다.
        """
        # 1. DB에 저장된 확실한 앱 객체를 가져옴
        app = self.get_app(request, sociallogin.account.provider)
        
        # 2. 토큰에 앱 연결 (ID가 있는 객체이므로 안전함)
        sociallogin.token.app = app
        
        # 3. 사이트 연결 재확인 (ManyToMany 관계 안전하게 사용 가능)
        current_site = get_current_site(request)
        if not app.sites.filter(id=current_site.id).exists():
            app.sites.add(current_site)

        super().pre_social_login(request, sociallogin)

    @transaction.atomic
    def save_user(self, request, sociallogin, form=None):
        """
        사용자 저장 및 GitHub 데이터 동기화
        """
        user = super().save_user(request, sociallogin, form)
        
        try:
            access_token = sociallogin.token.token
            
            if not access_token:
                logger.warning("GitHub access token not found for user %s.", user.username)
                return user

            g = Github(access_token)
            github_user = g.get_user()

            # 1. 사용자 정보 업데이트
            user.github_id = github_user.id
            user.github_username = github_user.login
            user.avatar_url = github_user.avatar_url
            user.save()

            # 2. 리포지토리 동기화
            self.sync_all_user_data(github_user)

        except Exception as e:
            logger.error("Critical error during GitHub data synchronization for user %s: %s", user.username, e, exc_info=True)
            # raise # 필요 시 주석 해제
            
        return user

    def sync_all_user_data(self, github_user):
        logger.info("Starting repository sync for user: %s", github_user.login)
        repos = github_user.get_repos(affiliation='owner,collaborator,organization_member', sort='pushed', direction='desc')
        
        for repo in repos:
            try:
                with transaction.atomic():
                    repository_model = self.sync_repository(repo)
                    self.sync_contributors(repository_model, repo)
                    self.sync_commits(repository_model, repo)
            except Exception as e:
                logger.error("Failed to sync repository %s for user %s: %s", repo.full_name, github_user.login, e, exc_info=True)
        logger.info("Finished repository sync for user: %s", github_user.login)

    def sync_repository(self, repo_obj) -> Repository:
        owner_user = User.objects.filter(github_id=repo_obj.owner.id).first()
        repository, created = Repository.objects.update_or_create(
            github_id=repo_obj.id,
            defaults={
                'name': repo_obj.name,
                'full_name': repo_obj.full_name,
                'description': repo_obj.description,
                'html_url': repo_obj.html_url,
                'stargazers_count': repo_obj.stargazers_count,
                'language': repo_obj.language,
                'created_at': repo_obj.created_at,
                'updated_at': repo_obj.updated_at,
                'owner': owner_user,
            }
        )
        return repository

    def sync_contributors(self, repository_model: Repository, repo_obj):
        try:
            contributors_from_api = list(repo_obj.get_contributors())
            if not contributors_from_api:
                return
            contributor_github_ids = [c.id for c in contributors_from_api if hasattr(c, 'id')]
            existing_users = User.objects.filter(github_id__in=contributor_github_ids)
            user_map = {user.github_id: user for user in existing_users}

            for contributor in contributors_from_api:
                if contributor.id in user_map:
                    user_obj = user_map[contributor.id]
                    Contributor.objects.update_or_create(
                        repository=repository_model,
                        user=user_obj,
                        defaults={'commit_count': contributor.contributions}
                    )
        except GithubException as e:
            logger.warning("Could not get contributors for %s. Error: %s", repo_obj.full_name, e)
        except Exception as e:
            logger.error("Unexpected error syncing contributors for %s: %s", repo_obj.full_name, e)

    def sync_commits(self, repository_model: Repository, repo_obj):
        try:
            commits_from_api = repo_obj.get_commits()
            if commits_from_api.totalCount == 0:
                repository_model.commit_count = 0
                repository_model.save(update_fields=['commit_count'])
                return
            repository_model.commit_count = commits_from_api.totalCount
            repository_model.save(update_fields=['commit_count'])

            author_github_ids = {c.author.id for c in commits_from_api if c.author}
            if not author_github_ids:
                return
            existing_users = User.objects.filter(github_id__in=author_github_ids)
            user_map = {user.github_id: user for user in existing_users}

            for commit in commits_from_api:
                commit_author_user = None
                if commit.author and commit.author.id in user_map:
                    commit_author_user = user_map[commit.author.id]
                Commit.objects.update_or_create(
                    sha=commit.sha,
                    defaults={
                        'repository': repository_model,
                        'author': commit_author_user,
                        'message': commit.commit.message,
                        'committed_at': commit.commit.author.date,
                        'author_name': commit.commit.author.name,
                        'author_email': commit.commit.author.email,
                    }
                )
        except GithubException as e:
            logger.warning("Could not get commits for %s. Error: %s", repo_obj.full_name, e)
        except Exception as e:
            logger.error("Unexpected error syncing commits for %s: %s", repo_obj.full_name, e)


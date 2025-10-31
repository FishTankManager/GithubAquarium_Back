# apps/users/adapter.py
import logging
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.db import transaction
from github import Github, GithubException
from apps.repositories.models import Repository, Contributor, Commit
from apps.repositories.serializers import RepositorySerializer, ContributorSerializer, CommitSerializer

logger = logging.getLogger(__name__)
User = get_user_model()

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    
    @transaction.atomic
    def save_user(self, request, sociallogin, form=None):
        """
        소셜 로그인 시 호출되며, User 모델에 추가 정보를 저장하고,
        PyGithub 라이브러리를 사용하여 관련 데이터를 동기화합니다.
        모든 과정은 원자적 트랜잭션으로 처리됩니다.
        """
        user = super().save_user(request, sociallogin, form)
        
        try:
            github_account = sociallogin.account
            access_token = github_account.extra_data.get('access_token')
            
            if not access_token:
                logger.warning("GitHub access token not found for user %s.", user.username)
                return user

            g = Github(access_token)
            github_user = g.get_user()

            # 1. User 모델 업데이트
            user.github_id = github_user.id
            user.github_username = github_user.login
            user.avatar_url = github_user.avatar_url
            user.save()

            # 2. Repository, Contributor, Commit 정보 동기화
            self.sync_repositories(user, github_user)

        except Exception as e:
            logger.error("Error during GitHub data synchronization for user %s: %s", user.username, e, exc_info=True)
            # 트랜잭션이 롤백되도록 예외를 다시 발생시킬 수 있습니다.
            # 또는 여기서 처리를 중단하고 사용자에게 오류를 알릴 수 있습니다.
            
        return user

    def sync_repositories(self, user, github_user):
        """
        사용자의 모든 저장소 정보를 가져와 DB에 업데이트합니다.
        """
        logger.info("Starting repository sync for user: %s", user.username)
        
        repos = github_user.get_repos(affiliation='owner', sort='updated', direction='desc')
        
        for repo in repos:
            try:
                with transaction.atomic():
                    repo_data = {
                        'github_id': repo.id,
                        'name': repo.name,
                        'full_name': repo.full_name,
                        'description': repo.description,
                        'html_url': repo.html_url,
                        'stargazers_count': repo.stargazers_count,
                        'language': repo.language,
                        'created_at': repo.created_at,
                        'updated_at': repo.updated_at,
                        'owner': user.id,
                    }
                    
                    instance = Repository.objects.filter(github_id=repo.id).first()
                    serializer = RepositorySerializer(instance=instance, data=repo_data)
                    
                    if serializer.is_valid(raise_exception=True):
                        repository = serializer.save()
                        
                        if not instance:
                            logger.info("Created new repository: %s", repo.full_name)
                        else:
                            logger.info("Updated repository: %s", repo.full_name)
                        
                        self.sync_contributors(repository, repo)
                        self.sync_commits(repository, repo)
            except Exception as e:
                logger.error("Failed to sync repository %s for user %s: %s", repo.full_name, user.username, e, exc_info=True)

        logger.info("Finished repository sync for user: %s", user.username)

    def sync_contributors(self, repository_model, repo_obj):
        """
        저장소의 Contributor 정보를 가져와 DB에 업데이트합니다.
        """
        logger.info("  Syncing contributors for %s", repo_obj.full_name)
        try:
            with transaction.atomic():
                contributors = repo_obj.get_contributors()
                for contributor in contributors:
                    user_instance = User.objects.filter(github_id=contributor.id).first()
                    
                    if user_instance:
                        contributor_data = {
                            'repository': repository_model.id,
                            'user': user_instance.id,
                            'github_username': contributor.login,
                            'contributions_count': contributor.contributions,
                            'avatar_url': contributor.avatar_url,
                        }
                        
                        instance = Contributor.objects.filter(repository=repository_model, user=user_instance).first()
                        serializer = ContributorSerializer(instance=instance, data=contributor_data)
                        
                        if serializer.is_valid(raise_exception=True):
                            serializer.save()

                logger.info("  Successfully synced contributors for %s", repo_obj.full_name)
        except GithubException as e:
            logger.warning("  Could not get contributors for %s. It might be empty. Error: %s", repo_obj.full_name, e)
        except Exception as e:
            logger.error("  An unexpected error occurred while syncing contributors for %s: %s", repo_obj.full_name, e, exc_info=True)

    def sync_commits(self, repository_model, repo_obj):
        """
        저장소의 Commit 정보를 가져와 DB에 업데이트합니다. (최근 100개)
        """
        logger.info("  Syncing commits for %s", repo_obj.full_name)
        try:
            with transaction.atomic():
                commits = repo_obj.get_commits()
                
                for commit in commits:
                    author_instance = None
                    if commit.author:
                        author_instance = User.objects.filter(github_id=commit.author.id).first()

                    author_name = commit.commit.author.name if commit.commit and commit.commit.author else "Unknown"
                    author_email = commit.commit.author.email if commit.commit and commit.commit.author else "unknown@example.com"

                    commit_data = {
                        'sha': commit.sha,
                        'repository': repository_model.id,
                        'author': author_instance.id if author_instance else None,
                        'message': commit.commit.message,
                        'committed_at': commit.commit.author.date,
                        'author_name': author_name,
                        'author_email': author_email,
                    }

                    instance = Commit.objects.filter(sha=commit.sha).first()
                    serializer = CommitSerializer(instance=instance, data=commit_data)

                    if serializer.is_valid(raise_exception=True):
                        serializer.save()

                logger.info("  Successfully synced commits for %s", repo_obj.full_name)
        except GithubException as e:
            logger.warning("  Could not get commits for %s. It might be empty. Error: %s", repo_obj.full_name, e)
        except Exception as e:
            logger.error("  An unexpected error occurred while syncing commits for %s: %s", repo_obj.full_name, e, exc_info=True)
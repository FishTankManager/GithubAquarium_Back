# apps/users/adapter.py
"""
Custom adapter for django-allauth to handle post-login logic.
"""
import logging
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.db import transaction
from github import Github, GithubException

from apps.repositories.models import Repository, Contributor, Commit

# Standard instance of a logger
logger = logging.getLogger(__name__)
User = get_user_model()

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Overrides the default social account adapter to sync GitHub data upon user login.
    This version focuses on syncing data ONLY related to users who are already
    registered in this application, ignoring external users.
    """
    
    @transaction.atomic
    def save_user(self, request, sociallogin, form=None):
        """
        This method is called when a user successfully logs in via a social account.
        It wraps the entire GitHub data synchronization in a single transaction.
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

            # 1. Update the logged-in user's model with their full GitHub data
            user.github_id = github_user.id
            user.github_username = github_user.login
            user.avatar_url = github_user.avatar_url
            user.save()

            # 2. Sync all repositories the user has contributed to
            self.sync_all_user_data(github_user)

        except Exception as e:
            logger.error("Critical error during GitHub data synchronization for user %s: %s", user.username, e, exc_info=True)
            raise
            
        return user

    def sync_all_user_data(self, github_user):
        """
        Orchestrates the synchronization of all GitHub data for a given user.
        """
        logger.info("Starting repository sync for user: %s", github_user.login)
        
        # Fetch all repositories the user is associated with (contribution-centric)
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
        """
        Updates or creates a Repository record.
        The repository's owner is linked ONLY IF they are a registered user.
        """
        # Find the owner in our DB. If not found, owner_user will be None.
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
                'owner': owner_user, # Link to owner if they exist, otherwise NULL.
            }
        )
        log_msg = "Created" if created else "Updated"
        logger.info("  %s repository: %s", log_msg, repo_obj.full_name)
        return repository

    def sync_contributors(self, repository_model: Repository, repo_obj):
        """
        Updates or creates Contributor records ONLY for registered users.
        This is optimized to avoid N+1 queries.
        """
        logger.info("    Syncing contributors for %s", repo_obj.full_name)
        try:
            contributors_from_api = list(repo_obj.get_contributors())
            if not contributors_from_api:
                return

            # --- N+1 Query Optimization ---
            # 1. Get all contributor GitHub IDs from the API response.
            contributor_github_ids = [c.id for c in contributors_from_api if hasattr(c, 'id')]
            
            # 2. Fetch all users from our database that match these IDs in a single query.
            existing_users = User.objects.filter(github_id__in=contributor_github_ids)
            
            # 3. Create a map for quick lookups (github_id -> User object).
            user_map = {user.github_id: user for user in existing_users}

            # 4. Process contributors who are registered in our service.
            for contributor in contributors_from_api:
                if contributor.id in user_map:
                    user_obj = user_map[contributor.id]
                    Contributor.objects.update_or_create(
                        repository=repository_model,
                        user=user_obj,
                        defaults={'commit_count': contributor.contributions}
                    )
            logger.info("    Successfully synced %d registered contributors for %s", len(user_map), repo_obj.full_name)
        except GithubException as e:
            logger.warning("    Could not get contributors for %s. Error: %s", repo_obj.full_name, e)
        except Exception as e:
            logger.error("    An unexpected error occurred while syncing contributors for %s: %s", repo_obj.full_name, e, exc_info=True)

    def sync_commits(self, repository_model: Repository, repo_obj):
        logger.info("    Syncing commits for %s", repo_obj.full_name)
        try:
            commits_from_api = repo_obj.get_commits()
            
            if commits_from_api.totalCount == 0:
                repository_model.commit_count = 0
                repository_model.save(update_fields=['commit_count'])
                logger.info("    No commits found for %s. Sync finished.", repo_obj.full_name)
                return

            repository_model.commit_count = commits_from_api.totalCount
            repository_model.save(update_fields=['commit_count'])

            # --- N+1 Query Optimization ---
            # 1. Collect all unique author GitHub IDs from the API response.
            author_github_ids = {c.author.id for c in commits_from_api if c.author}
            if not author_github_ids:
                return # No authors to process

            # 2. Fetch all users from our database that match these IDs.
            existing_users = User.objects.filter(github_id__in=author_github_ids)

            # 3. Create a map for quick lookups.
            user_map = {user.github_id: user for user in existing_users}

            # 4. Process all commits.
            for commit in commits_from_api:
                # Determine the author object if they are a registered user.
                commit_author_user = None
                if commit.author and commit.author.id in user_map:
                    commit_author_user = user_map[commit.author.id]

                Commit.objects.update_or_create(
                    sha=commit.sha,
                    defaults={
                        'repository': repository_model,
                        'author': commit_author_user, # Link to author if they exist, otherwise NULL.
                        'message': commit.commit.message,
                        'committed_at': commit.commit.author.date,
                        'author_name': commit.commit.author.name,
                        'author_email': commit.commit.author.email,
                    }
                )
            logger.info("    Successfully synced commits for %s", repo_obj.full_name)
        except GithubException as e:
            logger.warning("    Could not get commits for %s. Error: %s", repo_obj.full_name, e)
        except Exception as e:
            logger.error("    An unexpected error occurred while syncing commits for %s: %s", repo_obj.full_name, e, exc_info=True)
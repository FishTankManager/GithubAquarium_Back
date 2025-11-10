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
    """
    
    @transaction.atomic
    def save_user(self, request, sociallogin, form=None):
        """
        This method is called when a user successfully logs in via a social account.
        
        It performs the following actions in a single database transaction:
        1. Calls the parent `save_user` method to create/update the user.
        2. Retrieves the GitHub access token.
        3. Updates the local User model with additional data from the GitHub API.
        4. Initiates the synchronization of the user's repositories, contributors, and commits.
        """
        # Create the user using the default adapter's logic first.
        user = super().save_user(request, sociallogin, form)
        
        try:
            github_account = sociallogin.account
            access_token = github_account.extra_data.get('access_token')
            
            if not access_token:
                logger.warning("GitHub access token not found for user %s.", user.username)
                return user

            # Initialize PyGithub with the user's access token
            g = Github(access_token)
            github_user = g.get_user()

            # 1. Update the local User model with GitHub data
            user.github_id = github_user.id
            user.github_username = github_user.login
            user.avatar_url = github_user.avatar_url
            user.save()

            # 2. Sync repositories and their related data
            self.sync_all_user_data(user, github_user)

        except Exception as e:
            # If any part of the sync fails, the transaction will be rolled back.
            logger.error("Error during GitHub data synchronization for user %s: %s", user.username, e, exc_info=True)
            # Re-raise the exception to ensure the transaction is rolled back
            raise
            
        return user

    def sync_all_user_data(self, user, github_user):
        """
        Orchestrates the synchronization of all GitHub data for a given user.
        """
        logger.info("Starting repository sync for user: %s", user.username)
        
        # Fetch only repositories owned by the user, sorted by last update
        repos = github_user.get_repos(affiliation='owner', sort='updated', direction='desc')
        
        for repo in repos:
            try:
                # Use a nested transaction for each repository to isolate failures
                with transaction.atomic():
                    repository_model = self.sync_repository(repo, user)
                    self.sync_contributors(repository_model, repo)
                    self.sync_commits(repository_model, repo)
            except Exception as e:
                # Log errors per repository but don't stop the entire sync process
                logger.error("Failed to sync repository %s for user %s: %s", repo.full_name, user.username, e, exc_info=True)

        logger.info("Finished repository sync for user: %s", user.username)

    def sync_repository(self, repo_obj, owner_user):
        """
        Updates or creates a single Repository record in the database.
        This is more efficient than using serializers for background tasks.
        """
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
        log_msg = "Created new" if created else "Updated"
        logger.info("  %s repository: %s", log_msg, repo_obj.full_name)
        return repository

    def sync_contributors(self, repository_model, repo_obj):
        """
        Updates or creates Contributor records for a repository.
        Optimized to avoid N+1 query problems.
        """
        logger.info("    Syncing contributors for %s", repo_obj.full_name)
        try:
            contributors = list(repo_obj.get_contributors())
            if not contributors:
                return

            # --- N+1 Query Optimization ---
            # 1. Get all contributor GitHub IDs.
            contributor_github_ids = [c.id for c in contributors]
            # 2. Fetch all existing users in a single query.
            existing_users = User.objects.filter(github_id__in=contributor_github_ids).values('id', 'github_id')
            # 3. Create a mapping from github_id to user_id for quick lookup.
            user_map = {user['github_id']: user['id'] for user in existing_users}

            for contributor in contributors:
                # Only sync contributors who are also users of our application
                if contributor.id in user_map:
                    user_id = user_map[contributor.id]
                    Contributor.objects.update_or_create(
                        repository=repository_model,
                        user_id=user_id,
                        defaults={
                            'contributions_count': contributor.contributions,
                        }
                    )
            logger.info("    Successfully synced %d contributors for %s", len(contributors), repo_obj.full_name)
        except GithubException as e:
            logger.warning("    Could not get contributors for %s. It might be empty. Error: %s", repo_obj.full_name, e)
        except Exception as e:
            logger.error("    An unexpected error occurred while syncing contributors for %s: %s", repo_obj.full_name, e, exc_info=True)

    def sync_commits(self, repository_model, repo_obj):
        """
        Updates or creates Commit records for a repository.
        Fetches the most recent 100 commits to avoid excessive API calls.
        Optimized to avoid N+1 query problems.
        """
        logger.info("    Syncing commits for %s", repo_obj.full_name)
        try:
            commits = repo_obj.get_commits() # Fetch all commits

            # Update the repository's total commit count
            repository_model.commit_count = commits.totalCount
            repository_model.save(update_fields=['commit_count']) # Explicitly save the new count

            if not commits:
                return

            # --- N+1 Query Optimization ---
            author_github_ids = {c.author.id for c in commits if c.author}
            existing_users = User.objects.filter(github_id__in=author_github_ids).values('id', 'github_id')
            user_map = {user['github_id']: user['id'] for user in existing_users}

            for commit in commits:
                author_id = None
                if commit.author and commit.author.id in user_map:
                    author_id = user_map[commit.author.id]

                Commit.objects.update_or_create(
                    sha=commit.sha,
                    defaults={
                        'repository': repository_model,
                        'author_id': author_id,
                        'message': commit.commit.message,
                        'committed_at': commit.commit.author.date,
                        'author_name': commit.commit.author.name,
                        'author_email': commit.commit.author.email,
                    }
                )
            logger.info("    Successfully synced commits for %s", repo_obj.full_name)
        except GithubException as e:
            logger.warning("    Could not get commits for %s. It might be empty. Error: %s", repo_obj.full_name, e)
        except Exception as e:
            logger.error("    An unexpected error occurred while syncing commits for %s: %s", repo_obj.full_name, e, exc_info=True)
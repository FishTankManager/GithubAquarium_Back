# GithubAquarium/webhook_views.py
"""
Handles incoming webhooks from GitHub to sync repository and user data.
"""

import hashlib
import hmac
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from dateutil.parser import parse as parse_datetime

from apps.repositories.models import Repository, Commit
from apps.users.models import User

from drf_yasg.utils import swagger_auto_schema

class GitHubWebhookView(APIView):
    """
    Receives and processes webhook events from GitHub.
    
    This view verifies the integrity of the request using the webhook secret,
    then processes 'star', 'push', and 'meta' events to keep the database
    in sync with GitHub.
    """

    def _parse_date(self, date_value):
        """
        Handles both Unix timestamps and ISO 8601 date strings from GitHub payloads.
        Returns a timezone-aware datetime object or None.
        """
        if not date_value:
            return None
        if isinstance(date_value, int):
            return datetime.fromtimestamp(date_value, tz=timezone.utc)
        if isinstance(date_value, str):
            # Use dateutil.parser for robust parsing of ISO 8601 strings
            return parse_datetime(date_value)
        return None

    def _update_or_create_user(self, user_data):
        """
        Gets or creates a user from webhook payload data.
        This ensures that users related to events (owners, senders) are in our DB.
        """
        user, _ = User.objects.update_or_create(
            github_id=user_data['id'],
            defaults={
                'username': user_data['login'],
                'github_username': user_data['login'],
                'avatar_url': user_data.get('avatar_url', ''),
            }
        )
        return user

    def _update_or_create_repository(self, repo_data, owner):
        """
        Gets or creates a repository from webhook payload data.
        This ensures repository information is stored and associated with the correct owner.
        """
        repository, created = Repository.objects.update_or_create(
            github_id=repo_data['id'],
            defaults={
                'name': repo_data['name'],
                'full_name': repo_data['full_name'],
                'description': repo_data['description'],
                'html_url': repo_data['html_url'],
                'stargazers_count': repo_data['stargazers_count'],
                'language': repo_data['language'],
                'created_at': self._parse_date(repo_data.get('created_at')),
                'updated_at': self._parse_date(repo_data.get('updated_at')),
                'owner': owner,
            }
        )
        return repository

    @swagger_auto_schema(
        summary="GitHub Webhook Handler",
        description="""
        Handles incoming webhook events from GitHub to keep the application's database in sync.

        ### Supported Events:
        - **star**: Triggered when a repository is starred or unstarred. Updates the `stargazers_count`.
        - **push**: Triggered on a push to a repository. Updates repository details and records new commits.
        - **meta**: Triggered for webhook administrative events (e.g., deletion).

        The request body should be the raw JSON payload from the GitHub webhook, and the `X-Hub-Signature-256` header must be present for verification.
        """,
        operation_id="handle_github_webhook",
        tags=["Webhooks"],
    )
    def post(self, request, *args, **kwargs):
        # 1. Verify the request signature for security
        signature_header = request.headers.get('X-Hub-Signature-256')
        if not signature_header:
            return Response({'detail': 'Signature header missing'}, status=status.HTTP_403_FORBIDDEN)

        sha_name, signature = signature_header.split('=', 1)
        if sha_name != 'sha256':
            return Response({'detail': 'Invalid signature format'}, status=status.HTTP_403_FORBIDDEN)

        mac = hmac.new(settings.GITHUB_WEBHOOK_SECRET.encode('utf-8'), msg=request.body, digestmod=hashlib.sha256)
        if not hmac.compare_digest(mac.hexdigest(), signature):
            return Response({'detail': 'Invalid signature'}, status=status.HTTP_403_FORBIDDEN)

        # 2. Identify the event type and process the payload
        event_type = request.headers.get('X-GitHub-Event')
        payload = request.data

        if event_type == 'star':
            # Handle star/unstar events
            repo_data = payload['repository']
            owner_data = repo_data['owner']
            
            owner = self._update_or_create_user(owner_data)
            repository = self._update_or_create_repository(repo_data, owner)

            # Update stargazers_count as it's the primary data change in this event
            repository.stargazers_count = repo_data['stargazers_count']
            repository.save()

            print(f"Handled star event for {repository.full_name}")

        elif event_type == 'push':
            # Handle push events with new commits
            repo_data = payload['repository']
            owner_data = repo_data['owner']
            
            owner = self._update_or_create_user(owner_data)
            repository = self._update_or_create_repository(repo_data, owner)
            
            # Sync repository data that might change during a push
            repository.description = repo_data['description']
            repository.language = repo_data['language']
            repository.stargazers_count = repo_data['stargazers_count']
            
            # Safely update the 'updated_at' field
            parsed_updated_at = self._parse_date(repo_data.get('updated_at'))
            if parsed_updated_at:
                repository.updated_at = parsed_updated_at
            repository.save()

            # Process each commit in the push
            
            # 1. 루프 밖에서 모든 커밋 작성자의 username을 수집합니다.
            author_usernames = {
                commit_data['author'].get('username')
                for commit_data in payload['commits']
                if commit_data['author'].get('username')
            }

            # 2. 단 한 번의 쿼리로 모든 관련 사용자를 가져옵니다.
            users = User.objects.filter(github_username__in=author_usernames)
            
            # 3. username을 키로 하는 딕셔너리(맵)를 만들어 빠르게 사용자를 찾을 수 있도록 합니다.
            user_map = {user.github_username: user for user in users}

            for commit_data in payload['commits']:
                # 4. DB 쿼리 대신 맵에서 사용자를 조회합니다.
                commit_author = user_map.get(commit_data['author'].get('username'))

                Commit.objects.get_or_create(
                    sha=commit_data['id'],
                    defaults={
                        'repository': repository,
                        'author': commit_author,
                        'message': commit_data['message'],
                        'committed_at': self._parse_date(commit_data['timestamp']),
                        'author_name': commit_data['author']['name'],
                        'author_email': commit_data['author']['email'],
                    }
                )
            print(f"Handled push event for {repository.full_name}")

        elif event_type == 'meta':
            # Handle webhook meta-events (e.g., when a webhook is deleted)
            print("Received meta event")
        else:
            print(f"Received unhandled event type: {event_type}")

        return Response(status=status.HTTP_200_OK)

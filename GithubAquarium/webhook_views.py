# GithubAquarium/webhook_views.py
import hashlib
import hmac
import logging # Import the logging module
from django.conf import settings
from django_q.tasks import async_task
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


from drf_yasg.utils import swagger_auto_schema

# Get an instance of a logger for this module
logger = logging.getLogger(__name__)

class GitHubWebhookView(APIView):
    """
    Receives and processes webhook events from GitHub.
    
    This view verifies the integrity of the request using the webhook secret,
    then processes 'star', 'push', and 'meta' events to keep the database
    in sync with GitHub.
    """

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
        # 1. Verify Signature (보안 검증은 동기로 즉시 처리해야 함)
        signature_header = request.headers.get('X-Hub-Signature-256')
        if not signature_header:
            return Response({'detail': 'Signature header missing'}, status=status.HTTP_403_FORBIDDEN)

        sha_name, signature = signature_header.split('=', 1)
        if sha_name != 'sha256':
            return Response({'detail': 'Invalid signature format'}, status=status.HTTP_403_FORBIDDEN)

        mac = hmac.new(settings.GITHUB_WEBHOOK_SECRET.encode('utf-8'), msg=request.body, digestmod=hashlib.sha256)
        if not hmac.compare_digest(mac.hexdigest(), signature):
            return Response({'detail': 'Invalid signature'}, status=status.HTTP_403_FORBIDDEN)

        # 2. 작업 Queue에 등록
        event_type = request.headers.get('X-GitHub-Event')
        payload = request.data

        # 비동기 Task 호출
        async_task(
            'apps.repositories.tasks.process_webhook_event_task', # Task 함수 경로
            event_type,
            payload,
            group='webhooks' # 그룹을 지정하면 나중에 관리하기 편함
        )
        
        logger.info(f"Webhook event '{event_type}' queued for processing.")

        # 3. GitHub에 즉시 성공 응답 반환
        return Response({'detail': 'Event queued'}, status=status.HTTP_200_OK)
# GithubAquarium/webhook_views.py
import hashlib
import hmac
from django.conf import settings
from django_q.tasks import async_task
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema

class GitHubWebhookView(APIView):
    @swagger_auto_schema(
        operation_summary="GitHub 웹훅 수신",
        operation_description="GitHub로부터 push, star 이벤트를 수신하여 데이터를 비동기로 동기화합니다.",
        tags=["Webhooks"],
        responses={200: "수신 완료 및 큐 등록", 403: "서명 불일치"}
    )
    def post(self, request, *args, **kwargs):
        signature_header = request.headers.get('X-Hub-Signature-256')
        if not signature_header:
            return Response({'detail': 'Signature missing'}, status=403)
        mac = hmac.new(settings.GITHUB_WEBHOOK_SECRET.encode('utf-8'), msg=request.body, digestmod=hashlib.sha256)
        if not hmac.compare_digest(f"sha256={mac.hexdigest()}", signature_header):
            return Response({'detail': 'Invalid signature'}, status=403)

        event_type = request.headers.get('X-GitHub-Event')
        async_task('apps.repositories.tasks.process_webhook_event_task', event_type, request.data)
        return Response({'detail': 'Event queued'}, status=200)
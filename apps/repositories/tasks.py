# apps/repositories/tasks.py
import logging
from datetime import datetime
from dateutil.parser import parse as parse_datetime
from django.utils import timezone
from django.utils.timezone import make_aware, is_naive
from django.db.models import Q
from apps.repositories.models import Repository, Commit, Contributor
from apps.users.models import User

logger = logging.getLogger(__name__)

def process_webhook_event_task(event_type, payload):
    """
    Webhook 요청을 비동기로 처리하는 Task
    """
    try:
        if event_type == 'star':
            _handle_star_event(payload)
        elif event_type == 'push':
            _handle_push_event(payload)
        elif event_type == 'meta':
            logger.info("Meta event processed.")
        else:
            logger.warning(f"Unhandled event type in task: {event_type}")
    except Exception as e:
        logger.error(f"Error processing webhook event '{event_type}': {e}", exc_info=True)

# --- Helper Methods ---

def _parse_date(date_value):
    """
    다양한 포맷의 날짜를 Timezone-aware datetime 객체로 변환
    """
    if not date_value:
        return None
    
    dt = None
    if isinstance(date_value, int):
        # Timestamp case
        dt = datetime.fromtimestamp(date_value, tz=timezone.utc)
    elif isinstance(date_value, str):
        # String case (ISO 8601 etc)
        try:
            dt = parse_datetime(date_value)
        except (ValueError, TypeError):
            logger.warning(f"Failed to parse date: {date_value}")
            return None
    
    # Naive한 시간 객체라면 timezone 정보(UTC)를 붙여줍니다.
    if dt and is_naive(dt):
        dt = make_aware(dt, timezone.utc)
        
    return dt

def _get_existing_user(github_id=None, username=None):
    """
    Webhook Payload 정보로 DB에 이미 존재하는 유저를 찾음.
    없으면 None 반환 (Shell User 생성 안함).
    """
    if github_id:
        return User.objects.filter(github_id=github_id).first()
    if username:
        return User.objects.filter(github_username=username).first()
    return None

def _update_or_create_repository(repo_data, owner):
    default_branch = repo_data.get('default_branch', 'main')

    repository, created = Repository.objects.update_or_create(
        github_id=repo_data['id'],
        defaults={
            'name': repo_data['name'],
            'full_name': repo_data['full_name'],
            'description': repo_data.get('description', ''),
            'html_url': repo_data['html_url'],
            'stargazers_count': repo_data.get('stargazers_count', 0),
            'language': repo_data.get('language'),
            'default_branch': default_branch,
            'created_at': _parse_date(repo_data.get('created_at')),
            'updated_at': _parse_date(repo_data.get('updated_at')),
            'owner': owner, # User 객체 혹은 None
        }
    )
    return repository

def _handle_star_event(payload):
    repo_data = payload.get('repository')
    if not repo_data:
        return
        
    owner_data = repo_data.get('owner', {})
    # Shell User 생성 없이, 기존 유저 중에서만 검색
    owner = _get_existing_user(github_id=owner_data.get('id'), username=owner_data.get('login'))
    
    repository = _update_or_create_repository(repo_data, owner)

    repository.stargazers_count = repo_data.get('stargazers_count', 0)
    repository.save(update_fields=['stargazers_count'])
    logger.info(f"Updated star count for {repository.full_name}")

def _handle_push_event(payload):
    repo_data = payload.get('repository')
    if not repo_data:
        return

    # 1. 브랜치 필터링 (Main/Master Only)
    ref = payload.get('ref', '')
    branch_name = ref.split('/')[-1] if ref else ''
    
    payload_default_branch = repo_data.get('default_branch', 'main')
    allowed_branches = {payload_default_branch, 'main', 'master'}

    if branch_name not in allowed_branches:
        logger.debug(f"Skipping push event for non-default branch: {branch_name}")
        return

    # 2. Repository 정보 업데이트
    owner_data = repo_data.get('owner', {})
    owner = _get_existing_user(github_id=owner_data.get('id'), username=owner_data.get('login'))
    repository = _update_or_create_repository(repo_data, owner)
    
    # 3. Dirty Timestamp 업데이트
    # Webhook 도착 시점 기록 -> Sync Task에서 이 시간과 비교하여 무결성 판단
    push_timestamp = _parse_date(repo_data.get('pushed_at')) or timezone.now()

    if repository.dirty_at is None:
        repository.dirty_at = push_timestamp
    else:
        # 더 과거의 시간을 유지하여 Sync 범위 확보
        if push_timestamp < repository.dirty_at:
            repository.dirty_at = push_timestamp
    
    repository.save(update_fields=['dirty_at'])

    # 4. Commit 저장 및 Contributor 업데이트
    commits = payload.get('commits', [])
    if not commits:
        return

    # Bulk 처리를 위해 관련된 유저들을 미리 조회 (username OR email)
    author_usernames = set()
    author_emails = set()

    for c in commits:
        author = c.get('author', {})
        if author:
            if author.get('username'):
                author_usernames.add(author['username'])
            if author.get('email'):
                author_emails.add(author['email'])
    
    # DB에 존재하는 유저만 매핑 (Shell User 생성 안함)
    query_filter = Q()
    if author_usernames:
        query_filter |= Q(github_username__in=author_usernames)
    if author_emails:
        query_filter |= Q(email__in=author_emails)

    existing_users = User.objects.filter(query_filter)
    
    # 빠른 조회를 위한 매핑 테이블 생성
    user_map_by_username = {u.github_username: u for u in existing_users if u.github_username}
    user_map_by_email = {u.email: u for u in existing_users if u.email}

    for commit_data in commits:
        author_info = commit_data.get('author', {})
        username = author_info.get('username')
        email = author_info.get('email')
        
        # 1순위: username 매칭, 2순위: email 매칭
        commit_author = user_map_by_username.get(username)
        if not commit_author and email:
             commit_author = user_map_by_email.get(email)
        
        # 4-1. Commit 생성/업데이트
        Commit.objects.update_or_create(
            sha=commit_data['id'],
            defaults={
                'repository': repository,
                'author': commit_author,
                'message': commit_data.get('message', ''),
                'committed_at': _parse_date(commit_data.get('timestamp')),
                'author_name': author_info.get('name', ''),
                'author_email': author_info.get('email', ''),
            }
        )

        # 4-2. Contributor 존재 확인 (수정: 여기서 카운트를 증가시키지 않음)
        if commit_author:
            Contributor.objects.get_or_create(
                repository=repository,
                user=commit_author,
                defaults={'commit_count': 0}
            )
            # [Fix] Webhook에서는 카운트를 올리지 않습니다.
            # 카운트 집계와 보상 지급은 Sync Task(API 기반)가 수행하여
            # (API값 - DB값)의 차이만큼 정확히 보상하도록 합니다.

    logger.info(f"Processed push event for {repository.full_name} (Marked dirty at {repository.dirty_at})")
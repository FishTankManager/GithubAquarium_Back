# apps/users/tasks.py
import logging
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django_q.tasks import async_task
from github import Github, GithubException
from apps.repositories.models import Repository, Contributor, Commit
from apps.shop.models import UserCurrency, PointLog
from apps.aquatics.logic import update_or_create_contribution_fish

COMMIT_REWARD_PER_POINT = 10  # 1 커밋당 지급할 포인트

logger = logging.getLogger(__name__)
User = get_user_model()

def sync_github_data_task(user_id, access_token):
    """
    로그인 후 백그라운드에서 실행될 GitHub 전체 데이터 동기화 Task.
    Webhook으로 'Dirty'해진 상태를 정리하고, 누락된 커밋을 채워넣어 무결성을 맞춤.
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} does not exist.")
        return

    logger.info(f"Starting async repository sync for user: {user.username}")
    
    try:
        g = Github(access_token)
        github_user = g.get_user()
        
        # affiliation: owner, collaborator 등 모든 권한의 repo 가져오기
        # API 호출 최적화를 위해 최근 push된 순서로 정렬
        repos = github_user.get_repos(affiliation='owner,collaborator,organization_member', sort='pushed', direction='desc')

        for repo in repos:
            # 개별 레포지토리 단위로 격리하여 처리 (하나 실패해도 나머지는 진행)
            _process_single_repository(user, repo)

        logger.info(f"Finished async repository sync for user: {user.username}")

    except GithubException as e:
        logger.error(f"GitHub API error during sync for {user.username}: {e.status} {e.data}", exc_info=True)
    except Exception as e:
        logger.error(f"Critical error during async GitHub sync for {user.username}: {e}", exc_info=True)


def _process_single_repository(user, repo_obj):
    """
    하나의 레포지토리에 대한 동기화 과정을 트랜잭션으로 묶음.
    실패 시 트랜잭션은 롤백되지만, API Rate Limit 등의 이유라면 
    Dirty Flag를 설정하여 나중에 다시 시도하게 함.
    """
    repository_id = None  # 에러 발생 시 Dirty 마킹을 위해 ID 임시 저장

    try:
        with transaction.atomic():
            # 1. 레포지토리 기본 정보 동기화 (여기서 ID 확보)
            repository_model = _sync_repository(repo_obj)
            repository_id = repository_model.id

            # 2. Contributor 동기화 (API 호출 포함, 실패 시 예외 발생)
            _sync_contributors(repository_model, repo_obj)
            
            # 3. Commit 동기화 (API 호출 포함, 성공 시 Dirty 해제)
            _sync_commits(repository_model, repo_obj)

    except GithubException as e:
        # API Rate Limit (403, 429) 발생 시
        if e.status in [403, 429]:
            logger.warning(f"Rate limit hit for {repo_obj.full_name}. Rolling back and marking as dirty.")
            if repository_id:
                _mark_repository_dirty_safe(repository_id)
        else:
            logger.error(f"GitHub API error processing {repo_obj.full_name}: {e}")
            # 기타 API 에러의 경우에도 필요하다면 dirty 마킹을 할 수 있음
            if repository_id:
                _mark_repository_dirty_safe(repository_id)

    except Exception as e:
        logger.error(f"Unexpected error processing {repo_obj.full_name}: {e}", exc_info=True)
        # 예기치 못한 에러 시에도 나중에 재시도를 위해 Dirty 마킹
        if repository_id:
            _mark_repository_dirty_safe(repository_id)


def _mark_repository_dirty_safe(repo_id):
    """
    트랜잭션 외부에서 별도의 커밋으로 Dirty Flag를 설정함.
    """
    try:
        repo = Repository.objects.get(id=repo_id)
        # 이미 미래 시점으로 Dirty가 찍혀있지 않다면 현재 시간으로 설정
        if not repo.dirty_at:
            repo.dirty_at = timezone.now()
            repo.save(update_fields=['dirty_at'])
            logger.info(f"Repository {repo.full_name} marked dirty explicitly via task rescue.")
    except Repository.DoesNotExist:
        pass


# --- Helper Functions ---

def _sync_repository(repo_obj) -> Repository:
    # owner가 우리 DB에 있으면 연결, 없으면 None (Shell User 생성 안함)
    owner_id = repo_obj.owner.id
    owner_user = User.objects.filter(github_id=owner_id).first()
    
    default_branch = repo_obj.default_branch or 'main'

    repository, created = Repository.objects.update_or_create(
        github_id=repo_obj.id,
        defaults={
            'name': repo_obj.name,
            'full_name': repo_obj.full_name,
            'description': repo_obj.description,
            'html_url': repo_obj.html_url,
            'stargazers_count': repo_obj.stargazers_count,
            'language': repo_obj.language,
            'default_branch': default_branch,
            'created_at': repo_obj.created_at,
            'updated_at': repo_obj.updated_at,
            'owner': owner_user, # 없으면 None
        }
    )
    return repository

def _sync_contributors(repository_model: Repository, repo_obj):
    """
    Contributor 정보 동기화.
    API 에러 발생 시 try-except로 숨기지 않고 상위로 전파함.
    """
    # API 호출 (여기서 403/429 발생 가능)
    contributors_from_api = list(repo_obj.get_contributors())
    if not contributors_from_api:
        return
        
    contributor_github_ids = [c.id for c in contributors_from_api if hasattr(c, 'id')]
    existing_users = User.objects.filter(github_id__in=contributor_github_ids)
    user_map = {user.github_id: user for user in existing_users}

    for api_contributor in contributors_from_api:
        # 우리 서비스에 가입한 유저인 경우에만 처리
        if api_contributor.id in user_map:
            user_obj = user_map[api_contributor.id]
            new_count = api_contributor.contributions
            
            # 1. Contributor 객체 가져오기 (없으면 생성)
            contributor, created = Contributor.objects.get_or_create(
                repository=repository_model,
                user=user_obj,
                defaults={'commit_count': 0}
            )

            # 2. 커밋 증가분 계산 및 보상 지급
            if new_count > contributor.commit_count:
                diff = new_count - contributor.commit_count
                
                # 보상은 양수일 때만 지급 (커밋 삭제 등으로 줄어든 경우는 무시)
                if diff > 0:
                    reward_amount = diff * COMMIT_REWARD_PER_POINT
                    
                    # 재화 지급
                    currency, _ = UserCurrency.objects.get_or_create(user=user_obj)
                    currency.balance += reward_amount
                    currency.total_earned += reward_amount
                    currency.save()
                    
                    # 로그 기록
                    PointLog.objects.create(
                        user=user_obj,
                        amount=reward_amount,
                        reason=PointLog.Reason.COMMIT_REWARD,
                        description=f"{repository_model.name}: +{diff} commits"
                    )
                    
                    logger.info(f"Rewarded {user_obj.username} {reward_amount} points for {diff} new commits in {repository_model.name}.")

            # 3. 최신 커밋 카운트 DB 반영
            if contributor.commit_count != new_count:
                contributor.commit_count = new_count
                contributor.save(update_fields=['commit_count'])
                
            # [추가] 물고기 진화/할당 로직 호출
            contributor_model = Contributor.objects.get(repository=repository_model, user=user_obj)
            update_or_create_contribution_fish(contributor_model)
            
            # [추가] 개인 아쿠아리움 SVG 갱신 예약
            async_task('apps.aquatics.tasks.generate_aquarium_svg_task', user_obj.id)

    # [추가] 해당 레포지토리 공용 수족관 SVG 갱신 예약
    async_task('apps.aquatics.tasks.generate_fishtank_svg_task', repository_model.id)


def _sync_commits(repository_model: Repository, repo_obj):
    """
    커밋 동기화 로직 (Main/Master Only)
    Gap Filling 방식으로 최신 커밋부터 last_synced_hash까지 역순 조회.
    성공적으로 완료되면 dirty_at을 None으로 초기화.
    """
    sync_start_time = timezone.now()

    # 1. 대상 브랜치 확인
    target_branch = repository_model.default_branch or 'main'
    
    # 2. API 호출
    commits_from_api = repo_obj.get_commits(sha=target_branch)
    
    latest_sha_on_github = None
    gh_total_count = 0

    try:
        # totalCount 접근 시 API 호출 발생 가능
        if commits_from_api.totalCount == 0:
            logger.info(f"Repository {repository_model.full_name} is empty.")
            return
        
        gh_total_count = commits_from_api.totalCount
        latest_sha_on_github = commits_from_api[0].sha

    except IndexError:
        logger.info(f"Repository {repository_model.full_name} has no commits (IndexError).")
        return
    except GithubException as e:
        if e.status == 409: # Git Repository is empty
            return
        raise e # 상위로 전파

    # DB 상태 확인 (이미 최신이면 스킵)
    last_synced_hash = repository_model.last_synced_hash
    is_first_sync = (last_synced_hash is None)
    
    if repository_model.dirty_at is None and last_synced_hash == latest_sha_on_github:
        # 커밋 수는 다를 수 있으므로(force push 등) 카운트만 보정
        if repository_model.commit_count != gh_total_count:
            repository_model.commit_count = gh_total_count
            repository_model.save(update_fields=['commit_count'])
        logger.debug(f"Repository {repository_model.full_name} is up to date.")
        return

    logger.info(f"Syncing commits for {repository_model.full_name}")

    # 3. 커밋 순회 및 저장
    new_synced_hash = latest_sha_on_github 
    
    for commit in commits_from_api:
        sha = commit.sha

        # 앵커 도달 시 중단
        if not is_first_sync and sha == last_synced_hash:
            break
        
        # 작성자 매핑
        commit_author_user = None
        if commit.author: 
            commit_author_user = User.objects.filter(github_id=commit.author.id).first()
        
        Commit.objects.update_or_create(
            sha=sha,
            defaults={
                'repository': repository_model,
                'author': commit_author_user,
                'message': commit.commit.message,
                'committed_at': commit.commit.author.date,
                'author_name': commit.commit.author.name,
                'author_email': commit.commit.author.email,
            }
        )

    # 4. 무결성 마킹 업데이트 (트랜잭션 내부)
    # 명시적 Lock을 통해 동시성 제어
    repo_to_update = Repository.objects.select_for_update().get(id=repository_model.id)
    
    repo_to_update.last_synced_hash = new_synced_hash
    repo_to_update.commit_count = gh_total_count
    
    # [핵심] Sync 성공 시 Dirty 해제
    # 단, Sync 도중 Webhook이 들어와서 dirty_at을 더 미래 시간으로 바꿨다면 초기화하지 않음
    if repo_to_update.dirty_at and repo_to_update.dirty_at <= sync_start_time:
        repo_to_update.dirty_at = None
    
    repo_to_update.save(update_fields=['last_synced_hash', 'dirty_at', 'commit_count'])
    logger.info(f"Sync complete for {repository_model.full_name}. New anchor: {new_synced_hash[:7]}")
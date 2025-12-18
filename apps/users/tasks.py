# apps/users/tasks.py
import logging
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from github import Github, GithubException
from apps.repositories.models import Repository, Contributor, Commit
from apps.shop.models import UserCurrency, PointLog

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
        repos = github_user.get_repos(affiliation='owner,collaborator,organization_member', sort='pushed', direction='desc')

        for repo in repos:
            try:
                # 트랜잭션 단위로 처리하여 데이터 무결성 보장
                # (각 레포지토리 처리가 독립적으로 성공/실패하도록 함)
                _process_single_repository(user, repo)
            except Exception as e:
                logger.error(f"Failed to sync repository {repo.full_name}: {e}")

        logger.info(f"Finished async repository sync for user: {user.username}")

    except GithubException as e:
        logger.error(f"GitHub API error during sync for {user.username}: {e.status} {e.data}", exc_info=True)
    except Exception as e:
        logger.error(f"Critical error during async GitHub sync for {user.username}: {e}", exc_info=True)


def _process_single_repository(user, repo_obj):
    """
    하나의 레포지토리에 대한 동기화 과정을 트랜잭션으로 묶음
    """
    with transaction.atomic():
        repository_model = _sync_repository(repo_obj)
        _sync_contributors(repository_model, repo_obj)
        _sync_commits(repository_model, repo_obj)


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
    try:
        # API 호출 최적화를 위해 필요한 필드만 확인 (id, contributions)
        # 대규모 레포지토리의 경우 페이지네이션 주의 필요 (현재는 전체 순회)
        contributors_from_api = list(repo_obj.get_contributors())
        if not contributors_from_api:
            return
            
        contributor_github_ids = [c.id for c in contributors_from_api if hasattr(c, 'id')]
        existing_users = User.objects.filter(github_id__in=contributor_github_ids)
        user_map = {user.github_id: user for user in existing_users}

        for api_contributor in contributors_from_api:
            if api_contributor.id in user_map:
                user_obj = user_map[api_contributor.id]
                new_count = api_contributor.contributions
                
                # 1. Contributor 객체 가져오기 (없으면 생성, 초기값 0)
                contributor, created = Contributor.objects.get_or_create(
                    repository=repository_model,
                    user=user_obj,
                    defaults={'commit_count': 0} # 생성 시점에는 0으로 두고 아래에서 업데이트
                )

                # 2. 커밋 증가분 계산
                # (API에서 가져온 값이 DB 값보다 클 때만 보상 지급 - 커밋 삭제 등 예외 상황 방어)
                if new_count > contributor.commit_count:
                    diff = new_count - contributor.commit_count
                    
                    # 생성된 직후(created=True)라면 diff는 new_count 그 자체임
                    # 만약 '최초 가입 시 과거 커밋에 대한 보상을 줄 것인가?' -> MVP에서는 준다고 가정
                    # 안 주려면 if not created 조건을 걸어야 함. 여기서는 "주는" 방향으로 구현.
                    
                    reward_amount = diff * COMMIT_REWARD_PER_POINT
                    
                    if reward_amount > 0:
                        # 3. 재화 지급 (Atomic하게 처리 권장되나 Task 내부이므로 순차처리 가정)
                        currency, _ = UserCurrency.objects.get_or_create(user=user_obj)
                        currency.balance += reward_amount
                        currency.total_earned += reward_amount
                        currency.save()
                        
                        # 4. 로그 기록
                        PointLog.objects.create(
                            user=user_obj,
                            amount=reward_amount,
                            reason=PointLog.Reason.COMMIT_REWARD,
                            description=f"{repository_model.name}: +{diff} commits"
                        )
                        
                        logger.info(f"Rewarded {user_obj.username} {reward_amount} points for {diff} new commits.")

                # 5. 최신 커밋 카운트 반영
                if contributor.commit_count != new_count:
                    contributor.commit_count = new_count
                    contributor.save(update_fields=['commit_count'])

    except GithubException as e:
        logger.warning(f"Could not get contributors for {repo_obj.full_name}: {e}")


def _sync_commits(repository_model: Repository, repo_obj):
    """
    커밋 동기화 로직 (Main/Master Only)
    전략: GitHub의 최신 커밋부터 역순으로 조회하다가 
          DB의 last_synced_hash를 만나면 중단 (Gap Filling).
    """
    # [Race Condition 방어] Sync 시작 시점 기록
    sync_start_time = timezone.now()

    try:
        # 1. 대상 브랜치 확인 (Default Branch만 취급)
        target_branch = repository_model.default_branch or 'main'
        
        # 2. GitHub API로 커밋 리스트 가져오기 (SHA 지정)
        commits_from_api = repo_obj.get_commits(sha=target_branch)
        
        # [수정] 빈 레포지토리 및 API 예외 처리
        latest_sha_on_github = None
        gh_total_count = 0

        try:
            if commits_from_api.totalCount == 0:
                logger.info(f"Repository {repository_model.full_name} is empty.")
                return
            
            # totalCount 접근 시 API 호출이 발생할 수 있음
            gh_total_count = commits_from_api.totalCount
            
            # 첫 번째 커밋 접근 (여기서 리스트가 비어있으면 IndexError 발생 가능)
            latest_sha_on_github = commits_from_api[0].sha

        except IndexError:
            # 리스트가 실제로 비어있는 경우
            logger.info(f"Repository {repository_model.full_name} has no commits (IndexError).")
            return
        except GithubException as e:
            # 409 Conflict: Git Repository is empty
            if e.status == 409:
                logger.info(f"Repository {repository_model.full_name} is empty (409 Conflict).")
                return
            raise e

        # DB 상태 확인
        last_synced_hash = repository_model.last_synced_hash
        is_first_sync = (last_synced_hash is None)
        
        # [최적화] 이미 최신 상태이고, Webhook으로 더럽혀지지 않았다면 스킵
        if repository_model.dirty_at is None and last_synced_hash == latest_sha_on_github:
            logger.debug(f"Repository {repository_model.full_name} is up to date.")
            if repository_model.commit_count != gh_total_count:
                repository_model.commit_count = gh_total_count
                repository_model.save(update_fields=['commit_count'])
            return

        logger.info(f"Syncing commits for {repository_model.full_name} (Branch: {target_branch})")

        # 3. 커밋 순회 및 저장
        new_synced_hash = latest_sha_on_github 
        
        for commit in commits_from_api:
            sha = commit.sha

            # [앵커 도달 검사]
            if not is_first_sync and sha == last_synced_hash:
                logger.info(f"Reached anchor commit {sha[:7]}. Integrity restored.")
                break
            
            # 작성자 정보 매핑 (없으면 None)
            commit_author_user = None
            if commit.author: 
                commit_author_user = User.objects.filter(github_id=commit.author.id).first()
            
            # 커밋 저장
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

        # 4. 무결성 마킹 업데이트 (Race Condition 방어 적용)
        # 명시적인 row-locking을 위해 select_for_update 사용
        repo_to_update = Repository.objects.select_for_update().get(id=repository_model.id)
        
        repo_to_update.last_synced_hash = new_synced_hash
        repo_to_update.commit_count = gh_total_count
        
        # [핵심] Sync 도중에 Webhook이 들어와서 dirty_at을 미래 시간으로 바꿨다면 초기화하지 않음
        if repo_to_update.dirty_at and repo_to_update.dirty_at <= sync_start_time:
            repo_to_update.dirty_at = None
        
        repo_to_update.save(update_fields=['last_synced_hash', 'dirty_at', 'commit_count'])
        logger.info(f"Sync complete for {repository_model.full_name}. New anchor: {new_synced_hash[:7]}")

    except GithubException as e:
        logger.warning(f"Could not get commits for {repo_obj.full_name}: {e.status} {e.data}")
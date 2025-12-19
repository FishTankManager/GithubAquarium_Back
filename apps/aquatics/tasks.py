# apps/aquatics/tasks.py
import logging
import os
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import Aquarium, Fishtank
from .renderers import render_aquarium_svg, render_fishtank_svg
from apps.repositories.models import Repository

# 로깅 설정
logger = logging.getLogger(__name__)
User = get_user_model()

def generate_aquarium_svg_task(user_id):
    """
    유저의 개인 아쿠아리움을 렌더링하여 저장합니다.
    """
    try:
        user = User.objects.get(id=user_id)
        aquarium, _ = Aquarium.objects.get_or_create(user=user)
        
        # 1. SVG 텍스트 생성
        svg_content = render_aquarium_svg(user)
        
        if not svg_content:
            logger.warning(f"Empty SVG content generated for Aquarium (User: {user.username})")
            return

        # 2. 파일 저장 경로 설정
        file_name = f"aquariums/aquarium_{user.id}.svg"
        path = os.path.join(settings.MEDIA_ROOT, file_name)
        
        # 3. 디렉토리 생성 및 파일 쓰기
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg_content)
        
        # 4. DB 업데이트
        aquarium.svg_path = file_name
        aquarium.save(update_fields=['svg_path', 'updated_at'])
        
        logger.info(f"Successfully generated Aquarium SVG for user {user.username}")

    except User.DoesNotExist:
        logger.error(f"User not found for generate_aquarium_svg_task: {user_id}")
    except Exception as e:
        logger.error(f"Error generating Aquarium SVG for user {user_id}: {e}", exc_info=True)


def generate_fishtank_svg_task(repo_id, user_id=None):
    """
    특정 레포지토리의 피시탱크 SVG를 생성합니다.
    
    - repo_id, user_id 모두 있음: 해당 유저의 피시탱크 뷰만 갱신
    - user_id가 None임: 해당 레포지토리를 구독 중인 '모든' 유저의 피시탱크 뷰 갱신
    """
    try:
        # user_id가 없으면(Webhook 등에서 전체 갱신 요청 시)
        if user_id is None:
            fishtanks = Fishtank.objects.filter(repository_id=repo_id)
            for ft in fishtanks:
                _generate_single_fishtank(repo_id, ft.user_id)
        else:
            # 특정 유저만 갱신
            _generate_single_fishtank(repo_id, user_id)

    except Exception as e:
        logger.error(f"Error in generate_fishtank_svg_task dispatch (Repo: {repo_id}): {e}", exc_info=True)


def _generate_single_fishtank(repo_id, user_id):
    """
    실제 피시탱크 SVG 생성 및 저장 로직 (내부 함수)
    """
    try:
        repo = Repository.objects.get(id=repo_id)
        user = User.objects.get(id=user_id)
        
        # Fishtank 레코드가 없으면 생성, 있으면 가져옴
        fishtank, _ = Fishtank.objects.get_or_create(repository=repo, user=user)
        
        # 유저 정보를 넘겨서 렌더링 (해당 유저의 배경 설정 등 반영)
        svg_content = render_fishtank_svg(repo, user)
        
        if not svg_content:
            return

        file_name = f"fishtanks/repo_{repo.id}_user_{user.id}.svg"
        path = os.path.join(settings.MEDIA_ROOT, file_name)
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg_content)
            
        fishtank.svg_path = file_name
        fishtank.save(update_fields=['svg_path', 'updated_at'])
        
        logger.info(f"Generated Fishtank SVG for Repo {repo.full_name} / User {user.username}")

    except (Repository.DoesNotExist, User.DoesNotExist):
        logger.error(f"Repo or User missing for Fishtank generation (Repo: {repo_id}, User: {user_id})")
    except Exception as e:
        logger.error(f"Error generating Fishtank SVG (Repo: {repo_id}, User: {user_id}): {e}", exc_info=True)
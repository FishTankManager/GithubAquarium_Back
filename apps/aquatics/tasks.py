# apps/aquatics/tasks.py
import os
from django.conf import settings
from .models import Aquarium, Fishtank
from .renderers import render_aquarium_svg, render_fishtank_svg

def generate_aquarium_svg_task(user_id):
    """유저의 개인 아쿠아리움을 렌더링하여 저장"""
    from apps.users.models import User
    user = User.objects.get(id=user_id)
    aquarium, _ = Aquarium.objects.get_or_create(user=user)
    
    svg_content = render_aquarium_svg(user)
    
    file_name = f"aquariums/aquarium_{user.id}.svg"
    path = os.path.join(settings.MEDIA_ROOT, file_name)
    
    # 디렉토리 생성
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    
    aquarium.svg_path = file_name
    aquarium.save()

def generate_fishtank_svg_task(repo_id):
    """레포지토리 수족관을 렌더링하여 저장"""
    from apps.repositories.models import Repository
    repo = Repository.objects.get(id=repo_id)
    fishtank, _ = Fishtank.objects.get_or_create(repository=repo)
    
    svg_content = render_fishtank_svg(repo)
    
    file_name = f"fishtanks/fishtank_{repo.id}.svg"
    path = os.path.join(settings.MEDIA_ROOT, file_name)
    
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg_content)
        
    fishtank.svg_path = file_name
    fishtank.save()
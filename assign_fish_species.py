#!/usr/bin/env python
"""
Django shell에서 사용할 FishSpecies 할당 스크립트

사용법:
1. Django shell 실행: uv run manage.py shell
2. 이 스크립트 내용을 복사해서 실행하거나
3. exec(open('assign_fish_species.py').read()) 실행

예시:
    assign_fish_to_user('your_github_username', 'repository_name', 'FishSpecies_name')
    또는
    assign_fish_to_user('your_github_username', 'repository_name', fish_species_id=1)
"""

from apps.users.models import User
from apps.repositories.models import Repository, Contributor
from apps.items.models import FishSpecies
from apps.aquatics.models import ContributionFish


def assign_fish_to_user(github_username, repository_name, fish_species_name=None, fish_species_id=None):
    """
    GitHub 아이디로 사용자에게 FishSpecies를 할당합니다.
    
    Args:
        github_username: GitHub 사용자명 (username 또는 github_username)
        repository_name: 레포지토리 이름 (name 또는 full_name)
        fish_species_name: FishSpecies 이름 (name 필드)
        fish_species_id: FishSpecies ID (fish_species_name 대신 사용 가능)
    
    Returns:
        생성되거나 업데이트된 ContributionFish 객체
    """
    # 1. User 찾기
    try:
        user = User.objects.get(github_username=github_username)
    except User.DoesNotExist:
        try:
            user = User.objects.get(username=github_username)
        except User.DoesNotExist:
            print(f"❌ 사용자를 찾을 수 없습니다: {github_username}")
            print("사용 가능한 사용자 목록:")
            for u in User.objects.all()[:10]:
                print(f"  - {u.username} (github: {u.github_username})")
            return None
    
    print(f"✅ 사용자 찾음: {user.username} (GitHub: {user.github_username})")
    
    # 2. Repository 찾기
    try:
        repo = Repository.objects.get(name=repository_name)
    except Repository.DoesNotExist:
        try:
            repo = Repository.objects.get(full_name=repository_name)
        except Repository.DoesNotExist:
            print(f"❌ 레포지토리를 찾을 수 없습니다: {repository_name}")
            print("사용 가능한 레포지토리 목록:")
            for r in Repository.objects.all()[:10]:
                print(f"  - {r.name} (full_name: {r.full_name})")
            return None
    
    print(f"✅ 레포지토리 찾음: {repo.name} ({repo.full_name})")
    
    # 3. Contributor 찾기 또는 생성
    contributor, created = Contributor.objects.get_or_create(
        user=user,
        repository=repo,
        defaults={'commit_count': 0}  # 기본값
    )
    
    if created:
        print(f"✅ Contributor 생성됨: {user.username} in {repo.name}")
    else:
        print(f"✅ Contributor 찾음: {user.username} in {repo.name} (commits: {contributor.commit_count})")
    
    # 4. FishSpecies 찾기
    if fish_species_id:
        try:
            fish_species = FishSpecies.objects.get(id=fish_species_id)
        except FishSpecies.DoesNotExist:
            print(f"❌ FishSpecies를 찾을 수 없습니다 (ID: {fish_species_id})")
            return None
    elif fish_species_name:
        try:
            fish_species = FishSpecies.objects.get(name=fish_species_name)
        except FishSpecies.DoesNotExist:
            print(f"❌ FishSpecies를 찾을 수 없습니다: {fish_species_name}")
            print("사용 가능한 FishSpecies 목록:")
            for fs in FishSpecies.objects.all()[:20]:
                print(f"  - ID: {fs.id}, Name: {fs.name}, Maturity: {fs.get_maturity_display()}, Required: {fs.required_commits}")
            return None
    else:
        print("❌ fish_species_name 또는 fish_species_id를 제공해주세요.")
        return None
    
    print(f"✅ FishSpecies 찾음: {fish_species.name} (Maturity: {fish_species.get_maturity_display()}, Required: {fish_species.required_commits} commits)")
    
    # 5. ContributionFish 생성 또는 업데이트
    contribution_fish, created = ContributionFish.objects.get_or_create(
        contributor=contributor,
        defaults={
            'fish_species': fish_species,
            'is_visible_in_fishtank': True,
            'is_visible_in_aquarium': True,
        }
    )
    
    if not created:
        # 이미 존재하면 업데이트
        contribution_fish.fish_species = fish_species
        contribution_fish.save()
        print(f"✅ ContributionFish 업데이트됨: {contribution_fish}")
    else:
        print(f"✅ ContributionFish 생성됨: {contribution_fish}")
    
    return contribution_fish


def list_available_fish_species():
    """사용 가능한 모든 FishSpecies 목록을 출력합니다."""
    print("\n=== 사용 가능한 FishSpecies 목록 ===")
    for fs in FishSpecies.objects.all().order_by('group_code', 'maturity'):
        print(f"ID: {fs.id:3d} | {fs.name:30s} | {fs.get_maturity_display():12s} | Required: {fs.required_commits:3d} commits | Group: {fs.group_code}")


def list_user_contributions(github_username):
    """특정 사용자의 모든 ContributionFish를 출력합니다."""
    try:
        user = User.objects.get(github_username=github_username)
    except User.DoesNotExist:
        try:
            user = User.objects.get(username=github_username)
        except User.DoesNotExist:
            print(f"❌ 사용자를 찾을 수 없습니다: {github_username}")
            return
    
    print(f"\n=== {user.username}의 ContributionFish 목록 ===")
    contributors = Contributor.objects.filter(user=user)
    for contrib in contributors:
        try:
            cf = contrib.contribution_fish
            print(f"Repository: {contrib.repository.name}")
            print(f"  Fish: {cf.fish_species.name} ({cf.fish_species.get_maturity_display()})")
            print(f"  Visible in Fishtank: {cf.is_visible_in_fishtank}")
            print(f"  Visible in Aquarium: {cf.is_visible_in_aquarium}")
            print()
        except ContributionFish.DoesNotExist:
            print(f"Repository: {contrib.repository.name} - Fish 없음")
            print()


# 사용 예시 출력
print("""
=== FishSpecies 할당 스크립트 ===

사용법:
1. assign_fish_to_user('github_username', 'repository_name', 'FishSpecies_name')
   예: assign_fish_to_user('junha', 'GithubAquarium_Back', 'Salmon')

2. assign_fish_to_user('github_username', 'repository_name', fish_species_id=1)
   예: assign_fish_to_user('junha', 'GithubAquarium_Back', fish_species_id=5)

3. list_available_fish_species() - 사용 가능한 모든 FishSpecies 목록 보기

4. list_user_contributions('github_username') - 특정 사용자의 할당된 물고기 목록 보기

""")





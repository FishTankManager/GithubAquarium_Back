# apps/aquatics/logic.py
import logging
from django.conf import settings
from apps.items.models import FishSpecies
from apps.aquatics.models import ContributionFish, UnlockedFish, Aquarium

logger = logging.getLogger(__name__)

def update_or_create_contribution_fish(contributor):
    """
    기여자의 커밋 수에 맞춰 물고기 종을 결정하고 ContributionFish를 업데이트합니다.
    획득한 물고기는 자동으로 유저의 아쿠아리움에 배치됩니다.
    """
    commit_count = contributor.commit_count
    user = contributor.user
    
    try:
        current_fish = getattr(contributor, 'contribution_fish', None)
        if current_fish:
            group_code = current_fish.fish_species.group_code
        else:
            group_code = getattr(settings, "DEFAULT_FISH_GROUP", "ShrimpWich")
    except Exception:
        group_code = getattr(settings, "DEFAULT_FISH_GROUP", "ShrimpWich")

    # 1. 커밋 수에 맞는 가장 높은 단계의 물고기 조회
    target_species = FishSpecies.objects.filter(
        group_code=group_code,
        required_commits__lte=commit_count
    ).order_by('-maturity').first()

    if not target_species:
        # 하나도 만족하지 못하면 Lv.1 강제 할당
        target_species = FishSpecies.objects.filter(group_code=group_code, maturity=1).first()

    if not target_species:
        logger.error(f"No FishSpecies found for group {group_code}")
        return None

    # [수정] 유저의 아쿠아리움 가져오기 (없으면 생성)
    user_aquarium, _ = Aquarium.objects.get_or_create(user=user)

    # 2. ContributionFish 생성 또는 업데이트
    if not current_fish:
        current_fish = ContributionFish.objects.create(
            contributor=contributor,
            fish_species=target_species,
            aquarium=user_aquarium,  # [핵심] 생성 시 아쿠아리움 연결
            is_visible_in_aquarium=True
        )
    else:
        # 이미 존재하는 물고기라면 종 업데이트
        if current_fish.fish_species != target_species:
            current_fish.fish_species = target_species
            current_fish.save()
        
        # 혹시 아쿠아리움 연결이 끊겨있다면 다시 연결 (기존 데이터 보정)
        if not current_fish.aquarium:
            current_fish.aquarium = user_aquarium
            current_fish.is_visible_in_aquarium = True
            current_fish.save()

    # 3. 도감(UnlockedFish) 업데이트
    UnlockedFish.objects.get_or_create(
        user=user,
        fish_species=target_species
    )

    return current_fish
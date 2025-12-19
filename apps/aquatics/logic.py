# apps/aquatics/logic.py
import logging
from apps.items.models import FishSpecies
from apps.aquatics.models import ContributionFish, UnlockedFish
from django.conf import settings 

logger = logging.getLogger(__name__)

def update_or_create_contribution_fish(contributor):
    """
    기여자의 커밋 수에 맞춰 물고기 종을 결정하고 ContributionFish를 업데이트합니다.
    """
    commit_count = contributor.commit_count
    
    try:
        current_fish = contributor.contribution_fish
        group_code = current_fish.fish_species.group_code
    except:
        current_fish = None
        # settings에 정의된 상수를 사용 (방안 A)
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

    # 2. ContributionFish 생성 또는 업데이트
    if not current_fish:
        current_fish = ContributionFish.objects.create(
            contributor=contributor,
            fish_species=target_species
        )
    else:
        if current_fish.fish_species != target_species:
            current_fish.fish_species = target_species
            current_fish.save()

    # 3. 도감(UnlockedFish) 업데이트
    UnlockedFish.objects.get_or_create(
        user=contributor.user,
        fish_species=target_species
    )

    return current_fish
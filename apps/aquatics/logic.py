# apps/aquatics/logic.py
import logging
import random
from django.conf import settings
from apps.items.models import FishSpecies
from apps.aquatics.models import ContributionFish, UnlockedFish, Aquarium

logger = logging.getLogger(__name__)

def update_or_create_contribution_fish(contributor):
    """
    기여자의 커밋 수에 맞춰 물고기 종을 결정하고 ContributionFish를 업데이트합니다.
    
    1. 신규 획득 시: DB에 존재하는 물고기 그룹 중 하나를 '랜덤'으로 배정합니다.
    2. 기존 보유 시: 이미 배정받은 그룹 내에서 진화(Maturity 증가)만 수행합니다.
    3. 획득한 물고기는 자동으로 유저의 아쿠아리움에 배치됩니다.
    """
    commit_count = contributor.commit_count
    user = contributor.user
    
    # 1. 물고기 그룹(Group Code) 결정
    # contributor에게 이미 할당된 물고기가 있는지 확인 (Related Object 참조)
    current_fish = getattr(contributor, 'contribution_fish', None)

    if current_fish:
        # 이미 물고기가 있다면, 기존 그룹을 유지 (진화만 함)
        group_code = current_fish.fish_species.group_code
    else:
        # [수정] 신규 할당: 등록된 모든 물고기 그룹 중 하나를 랜덤 선택
        available_groups = list(FishSpecies.objects.values_list('group_code', flat=True).distinct())
        
        if available_groups:
            group_code = random.choice(available_groups)
        else:
            # DB에 물고기 데이터가 하나도 없을 경우 대비 (Fallback)
            group_code = getattr(settings, "DEFAULT_FISH_GROUP", "ShrimpWich")

    # 2. 커밋 수에 맞는 가장 높은 단계(Maturity)의 물고기 조회
    # 예: 해당 그룹에서 내 커밋 수보다 요구량이 작거나 같은 것 중 가장 높은 단계
    target_species = FishSpecies.objects.filter(
        group_code=group_code,
        required_commits__lte=commit_count
    ).order_by('-maturity').first()

    if not target_species:
        # 조건에 맞는 게 없다면(커밋 0개 등), 해당 그룹의 1단계(Lv.1) 강제 할당
        target_species = FishSpecies.objects.filter(group_code=group_code, maturity=1).first()

    if not target_species:
        logger.error(f"No FishSpecies found for group {group_code}")
        return None

    # 3. 유저의 아쿠아리움 가져오기 (없으면 생성)
    user_aquarium, _ = Aquarium.objects.get_or_create(user=user)

    # 4. ContributionFish 생성 또는 업데이트
    if not current_fish:
        # 신규 생성
        current_fish = ContributionFish.objects.create(
            contributor=contributor,
            fish_species=target_species,
            aquarium=user_aquarium,  # [핵심] 생성 시 아쿠아리움에 바로 넣기
            is_visible_in_aquarium=True
        )
    else:
        # 기존 물고기 업데이트
        if current_fish.fish_species != target_species:
            current_fish.fish_species = target_species
            current_fish.save()
        
        # 혹시 아쿠아리움 연결이 끊겨있다면 다시 연결 (데이터 보정)
        if not current_fish.aquarium:
            current_fish.aquarium = user_aquarium
            current_fish.is_visible_in_aquarium = True
            current_fish.save()

    # 5. 도감(UnlockedFish) 업데이트 (Fishdex)
    UnlockedFish.objects.get_or_create(
        user=user,
        fish_species=target_species
    )

    return current_fish
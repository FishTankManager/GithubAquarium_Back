# apps/aquatics/models.py
from django.db import models
from django.conf import settings
from apps.repositories.models import Repository
from apps.items.models import Background, FishSpecies
from apps.repositories.models import Contributor


class UnlockedFish(models.Model):
    """
    Links a User to a FishSpecies they have unlocked (like a Fishdex).
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_fishes' # Note: Consider changing to 'unlocked_fishes' later if needed
    )
    fish_species = models.ForeignKey(
        FishSpecies,
        on_delete=models.CASCADE
    )
    unlocked_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the user unlocked this fish species."
    )

    class Meta:
        unique_together = ('user', 'fish_species')

    def __str__(self):
        return f"{self.user.username}'s unlocked {self.fish_species.name}"


class OwnBackground(models.Model):
    """
    Links a User to a Background they have unlocked and can use.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='owned_backgrounds'
    )
    background = models.ForeignKey(
        Background, 
        on_delete=models.CASCADE
    )
    unlocked_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the user unlocked this background."
    )

    class Meta:
        unique_together = ('user', 'background')

    def __str__(self):
        return f"{self.user.username}'s {self.background.name}"
    

class Aquarium(models.Model):
    """
    Represents a user's personal aquarium.
    It is uniquely identified by the 'user'.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='aquarium'
    )
    background = models.ForeignKey(
        OwnBackground, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="The background chosen by the user from their collection."
    )
    svg_path = models.CharField(
        max_length=512, 
        blank=True,
        help_text="The relative path to the generated SVG file."
    )
    updated_at = models.DateTimeField(auto_now=True) # 추가

    def __str__(self):
        return f"{self.user.username}'s Aquarium"


class Fishtank(models.Model):
    """
    특정 레포지토리에 대한 '개별 유저의 뷰'를 담당하는 수족관입니다.
    유저마다 같은 레포지토리를 서로 다른 배경으로 볼 수 있습니다.
    """
    repository = models.ForeignKey(
        Repository, 
        on_delete=models.CASCADE, 
        related_name='fishtanks'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='fishtanks'
    )
    background = models.ForeignKey(
        OwnBackground, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="이 수족관 뷰에 대해 유저가 설정한 배경입니다."
    )
    svg_path = models.CharField(
        max_length=512, 
        blank=True,
        help_text="유저의 설정이 반영되어 생성된 SVG 파일 경로."
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('repository', 'user')

    def __str__(self):
        return f"{self.user.username}'s view of {self.repository.name}"
    

class ContributionFish(models.Model):
    """
    Represents a contributor's assigned fish within a Fishtank.
    This fish can optionally be added to a user's personal Aquarium.
    """
    contributor = models.OneToOneField(
        Contributor,
        on_delete=models.CASCADE,
        related_name='contribution_fish'
    )
    fish_species = models.ForeignKey(
        FishSpecies, 
        on_delete=models.PROTECT,
        help_text="The species assigned to this contributor."
    )
    aquarium = models.ForeignKey(
        Aquarium,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fishes',
        help_text="The aquarium this fish has been added to."
    )
    is_visible_in_fishtank = models.BooleanField(
        default=True,
        help_text="Determines whether this fish is visible in the repository fishtank."
    )
    is_visible_in_aquarium = models.BooleanField(
        default=True,
        help_text="Determines whether this fish is visible in the personal aquarium."
    )

    def __str__(self):
        if self.aquarium:
            return f"Fish for {self.contributor.user.username} in {self.contributor.repository.name}'s Fishtank (in {self.aquarium})"
        return f"Fish for {self.contributor.user.username} in {self.contributor.repository.name}'s Fishtank"
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

    def __str__(self):
        return f"{self.user.username}'s Aquarium"


class Fishtank(models.Model):
    """
    Represents a shared fishtank for a single repository.
    It contains fish representing each contributor.
    """
    repository = models.OneToOneField(
        Repository, 
        on_delete=models.CASCADE, 
        related_name='fishtank'
    )
    svg_path = models.CharField(
        max_length=512, 
        blank=True,
        help_text="The relative path to the generated SVG file."
    )

    def __str__(self):
        return f"Fishtank for {self.repository.name}"

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
    is_visible = models.BooleanField(
        default=True,
        help_text="Determines whether this fish is visible in the fishtank."
    )

    def __str__(self):
        if self.aquarium:
            return f"Fish for {self.contributor.user.username} in {self.contributor.repository.name}'s Fishtank (in {self.aquarium})"
        return f"Fish for {self.contributor.user.username} in {self.contributor.repository.name}'s Fishtank"


class FishtankSetting(models.Model):
    """
    Stores a contributor's chosen background for a specific Fishtank.
    """
    fishtank = models.ForeignKey(
        Fishtank, 
        on_delete=models.CASCADE, 
        related_name='settings'
    )
    contributor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE
    )
    background = models.ForeignKey(
        OwnBackground, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="The background chosen by the contributor for this fishtank."
    )

    class Meta:
        unique_together = ('fishtank', 'contributor')

    def __str__(self):
        return f"Setting by {self.contributor.username} for {self.fishtank}"
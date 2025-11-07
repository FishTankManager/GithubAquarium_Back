# aquartics/models.py
from django.db import models
from django.conf import settings
from apps.repositories.models import Repository
from apps.items.models import FishSpecies, UserBackground

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
        UserBackground, 
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

class AquariumFish(models.Model):
    """
    Represents a single fish within an Aquarium.
    Each fish corresponds to a repository owned by the user.
    """
    aquarium = models.ForeignKey(
        Aquarium, 
        on_delete=models.CASCADE, 
        related_name='fishes'
    )
    repository = models.OneToOneField(
        Repository, 
        on_delete=models.CASCADE
    )
    fish_species = models.ForeignKey(
        FishSpecies, 
        on_delete=models.PROTECT,
        help_text="The species assigned to this repository-fish."
    )

    def __str__(self):
        return f"Fish for {self.repository.name} in {self.aquarium}"

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

class FishtankContributor(models.Model):
    """
    Represents a contributor's assigned fish within a Fishtank.
    An instance is uniquely identified by the combination of 'fishtank' and 'contributor'.
    """
    fishtank = models.ForeignKey(
        Fishtank, 
        on_delete=models.CASCADE, 
        related_name='contributors'
    )
    contributor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE
    )
    fish_species = models.ForeignKey(
        FishSpecies, 
        on_delete=models.PROTECT,
        help_text="The species assigned to this contributor."
    )

    class Meta:
        unique_together = ('fishtank', 'contributor')

    def __str__(self):
        return f"{self.contributor.username} in {self.fishtank}"

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
        UserBackground, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="The background chosen by the contributor for this fishtank."
    )

    class Meta:
        unique_together = ('fishtank', 'contributor')

    def __str__(self):
        return f"Setting by {self.contributor.username} for {self.fishtank}"
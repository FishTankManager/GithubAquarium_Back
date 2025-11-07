# items/models.py
from django.db import models
from django.conf import settings

class FishSpecies(models.Model):
    """
    Master data for all available fish species in the system (the "Fishdex").
    """
    name = models.CharField(
        max_length=100, 
        unique=True,
        help_text="The display name of the fish species."
    )
    species_code = models.CharField(
        max_length=10, 
        unique=True, 
        db_index=True,
        help_text="A short, unique code for programmatic access, e.g., 'C-KRAKEN'."
    )
    evolves_from = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='evolves_into',
        help_text="The species from which this one evolves."
    )
    svg_template = models.TextField(
        help_text="The SVG source code template for this fish."
    )

    def __str__(self):
        return f"[{self.species_code}] {self.name}"

class Background(models.Model):
    """
    Master data for all available backgrounds.
    """
    name = models.CharField(
        max_length=100, 
        unique=True,
        help_text="The display name of the background."
    )
    code = models.CharField(
        max_length=10, 
        unique=True, 
        db_index=True,
        help_text="A short, unique code for this background."
    )
    svg_template = models.TextField(
        help_text="The SVG source code template for this background."
    )

    def __str__(self):
        return self.name

class UserBackground(models.Model):
    """
    Links a User to a Background they have unlocked.
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
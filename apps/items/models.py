# apps/items/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class FishSpecies(models.Model):
    """
    Master data for all available fish species in the system (the "Fishdex").
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="The display name of the fish species."
    )
    group_code = models.CharField(
        max_length=10,
        db_index=True,
        help_text="A code for the evolution group, e.g., 'C-KRAKEN'.",
        default="NONE"
    )
    level = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="The evolution level of the fish, from 0 to 5."
    )
    required_commits = models.PositiveIntegerField(
        default=0,
        db_index=True,  # Add index for faster lookups based on commit counts.
        help_text="The total number of commits required to reach this evolution level."
    )
    
    svg_template = models.TextField(
        help_text="The SVG source code template for this fish."
    )

    class Meta:
        unique_together = [
            ('group_code', 'level'),
        ]

    def __str__(self):
        return f"[{self.group_code}-Lvl:{self.level}] {self.name} ({self.required_commits}+ commits)"

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

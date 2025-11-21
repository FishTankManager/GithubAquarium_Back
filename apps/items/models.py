from django.db import models

class FishSpecies(models.Model):
    """
    Master data for all available fish species in the system (the "Fishdex").
    """
    class Rarity(models.IntegerChoices):
        COMMON = 1, 'Common'
        UNCOMMON = 2, 'Uncommon'
        RARE = 3, 'Rare'
        EPIC = 4, 'Epic'
        LEGENDARY = 5, 'Legendary'

    class Maturity(models.IntegerChoices):
        HATCHLING = 0, 'Hatchling'
        JUVENILE = 1, 'Juvenile'
        YOUNGLING = 2, 'Youngling'
        ADULT = 3, 'Adult'
        ADVANCED = 4, 'Advanced'
        MASTER = 5, 'Master'

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
    maturity = models.IntegerField(
        choices=Maturity.choices,
        default=Maturity.HATCHLING,
        help_text="The evolution stage of the fish."
    )
    required_commits = models.PositiveIntegerField(
        default=0,
        db_index=True,
        help_text="The total number of commits required to reach this evolution stage."
    )
    rarity = models.IntegerField(
        choices=Rarity.choices,
        default=Rarity.COMMON,
        help_text="The rarity level of the fish species."
    )
    svg_template = models.TextField(
        help_text="The SVG source code template for this fish."
    )

    class Meta:
        unique_together = [
            ('group_code', 'maturity'),
        ]

    def __str__(self):
        return f"[{self.group_code}-{self.maturity}] {self.name} ({self.required_commits}+ commits)"

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
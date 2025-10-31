# apps/manager/models.py
from django.db import models

class Rarity(models.TextChoices):
    COMMON = "COMMON", "Common"
    RARE = "RARE", "Rare"
    EPIC = "EPIC", "Epic"
    LEGENDARY = "LEGENDARY", "Legendary"


class SvgAsset(models.Model):
    """
    운영진이 업로드해서 도감/상점/어항에서 공통으로 쓰는 SVG 원본
    """
    ASSET_TYPES = (
        ("FISH", "Fish"),
        ("BG", "Background"),
    )

    name = models.CharField(max_length=100, unique=True)
    asset_type = models.CharField(max_length=8, choices=ASSET_TYPES)
    svg = models.FileField(upload_to="svg/")
    width_px = models.PositiveIntegerField(default=50)
    height_px = models.PositiveIntegerField(default=50)
    rarity = models.CharField(
        max_length=16,
        choices=Rarity.choices,
        default=Rarity.COMMON,
    )
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "SVG 에셋"
        verbose_name_plural = "SVG 에셋"

    def __str__(self):
        return f"{self.asset_type}:{self.name}"


class FishSpecies(models.Model):
    """
    도감에서 보여줄 물고기 종류
    """
    name = models.CharField(max_length=100, unique=True)
    asset = models.ForeignKey(
        SvgAsset,
        on_delete=models.PROTECT,
        limit_choices_to={"asset_type": "FISH", "approved": True},
        related_name="fish_species",
    )
    rarity = models.CharField(
        max_length=16,
        choices=Rarity.choices,
        default=Rarity.COMMON,
    )
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "물고기 종류"
        verbose_name_plural = "물고기 종류"

    def __str__(self):
        return self.name


class BackgroundStyle(models.Model):
    """
    어항/수조에서 쓸 수 있는 배경 종류
    """
    name = models.CharField(max_length=100, unique=True)
    asset = models.ForeignKey(
        SvgAsset,
        on_delete=models.PROTECT,
        limit_choices_to={"asset_type": "BG", "approved": True},
        related_name="background_styles",
    )
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "배경 스타일"
        verbose_name_plural = "배경 스타일"

    def __str__(self):
        return self.name

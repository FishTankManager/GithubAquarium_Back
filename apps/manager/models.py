# apps/manager/models.py
from django.db import models

class Rarity(models.TextChoices):
    COMMON = "COMMON", "Common"
    RARE = "RARE", "Rare"
    EPIC = "EPIC", "Epic"
    LEGENDARY = "LEGENDARY", "Legendary"

class Maturity(models.TextChoices):
    """물고기 성장 단계"""
    HATCHLING = "HATCHLING", "Hatchling (새끼)"
    JUVENILE = "JUVENILE", "Juvenile (유어)"
    ADULT = "ADULT", "Adult (성체)"

class SvgAsset(models.Model):
    """
    운영진이 업로드해서 도감/상점/어항에서 공통으로 쓰는 SVG 원본
    """
    ASSET_TYPES = (
        ("FISH", "Fish"),
        ("BG", "Background"),
        ("ITEM", "Shop Item"),
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
    maturity = models.CharField(
        max_length=12,
        choices=Maturity.choices,
        null=True,
        blank=True,
        help_text="물고기(FISH)인 경우에만 선택합니다.",
    )
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "SVG 에셋"
        verbose_name_plural = "SVG 에셋"

    def __str__(self):
        return f"{self.asset_type}:{self.name}"

#도감
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
    spawn_weight = models.PositiveIntegerField(default=100, help_text="가중치가 높을수록 자주 나옵니다.")


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


##상점
class ShopItem(models.Model):
    """
    상점에서 판매할 아이템
    - 배경(BG) 또는 뽑기권(TICKET)
    - 대표 SVG 이미지 연결 가능
    """
    ITEM_TYPES = (
        ("BG", "Background"),
        ("TICKET", "Draw Ticket"),
    )

    name = models.CharField(max_length=100, unique=True)
    item_type = models.CharField(max_length=10, choices=ITEM_TYPES)
    price = models.PositiveIntegerField()
    asset = models.ForeignKey(
        SvgAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"approved": True},
        related_name="shop_items",
        help_text="상품의 대표 이미지로 사용할 SVG 선택",
    )
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "상점 아이템"
        verbose_name_plural = "상점 아이템"

    def __str__(self):
        return f"{self.name} ({self.get_item_type_display()})"
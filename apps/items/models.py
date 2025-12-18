from django.db import models
from django.core.validators import FileExtensionValidator

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
    background_image = models.ImageField(
        upload_to="backgrounds/",
        validators=[FileExtensionValidator(['png', 'jpg', 'jpeg'])],
        help_text="배경 이미지 파일(PNG/JPG).",
        null=True,
        blank=True
    )

    def __str__(self):
        return self.name

class Item(models.Model):
    class ItemType(models.TextChoices):
        REROLL_TICKET = 'REROLL', 'Re-roll Ticket'       # 물고기 리롤권
        BG_UNLOCK = 'BG_UNLOCK', 'Background Unlock'     # 배경 해금권

    code = models.CharField(max_length=50, unique=True, help_text="아이템 식별 코드 (예: TICKET_REROLL)")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    item_type = models.CharField(max_length=20, choices=ItemType.choices)
    
    # 가격 정보 (MVP 단계에서는 변동 가격 등 복잡한 로직 없이 고정 가격 사용)
    price = models.PositiveIntegerField(default=10, help_text="구매 가격 (Points)")
    
    # 배경 해금권일 경우, 어떤 배경을 해금하는지 연결
    # 리롤권이라면 이 필드는 비워둠 (Null)
    target_background = models.ForeignKey(
        Background, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="배경 해금권일 경우 연결된 배경 객체"
    )

    image = models.ImageField(upload_to='items/', null=True, blank=True)
    is_active = models.BooleanField(default=True, help_text="상점 노출 여부")

    def __str__(self):
        return f"[{self.item_type}] {self.name} ({self.price}P)"
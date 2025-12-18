from django.db import models
from django.conf import settings
from apps.items.models import Item  # items 앱 참조

class UserCurrency(models.Model):
    """
    유저의 재화 보유량
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='currency')
    balance = models.PositiveIntegerField(default=0)
    total_earned = models.PositiveIntegerField(default=0, help_text="누적 획득량(통계용)")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}: {self.balance} P"

class UserInventory(models.Model):
    """
    유저가 보유한 아이템 (수량 관리)
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='inventory')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'item') # 유저당 아이템별로 레코드 하나씩

    def __str__(self):
        return f"{self.user.username} has {self.quantity} x {self.item.name}"

class PointLog(models.Model):
    """
    재화 변동 로그 (Audit Log)
    """
    class Reason(models.TextChoices):
        COMMIT_REWARD = 'COMMIT', 'Commit Reward'
        SHOP_PURCHASE = 'BUY', 'Shop Purchase'
        ITEM_USE = 'USE', 'Item Usage' # 아이템 사용으로 인한 변동이 있을 경우(현재는 없음)
        ADMIN = 'ADMIN', 'Admin Adjustment'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.IntegerField(help_text="변동량 (양수: 획득, 음수: 소비)")
    reason = models.CharField(max_length=20, choices=Reason.choices)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
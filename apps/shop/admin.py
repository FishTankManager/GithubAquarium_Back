from django.contrib import admin
from .models import UserCurrency, UserInventory, PointLog

@admin.register(UserCurrency)
class UserCurrencyAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'total_earned', 'updated_at')
    search_fields = ('user__username',)
    readonly_fields = ('updated_at',)

@admin.register(UserInventory)
class UserInventoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'item', 'quantity')
    list_filter = ('item__item_type',)
    search_fields = ('user__username', 'item__name')

@admin.register(PointLog)
class PointLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'reason', 'description', 'created_at')
    list_filter = ('reason', 'created_at')
    search_fields = ('user__username', 'description')
    readonly_fields = ('user', 'amount', 'reason', 'description', 'created_at')

    # 로그는 관리자가 수정할 수 없도록 설정 (보안상 권장)
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
# apps/manager/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import SvgAsset, FishSpecies, BackgroundStyle, ShopItem


@admin.register(SvgAsset)
class SvgAssetAdmin(admin.ModelAdmin):
    list_display = ("name", "asset_type", "rarity", "approved", "size", "updated_at")
    list_filter = ("asset_type", "rarity", "approved")
    search_fields = ("name",)
    actions = ("approve_assets", "revoke_approval")

    def size(self, obj):
        return f"{obj.width_px}×{obj.height_px}"

    @admin.action(description="선택 SVG 승인")
    def approve_assets(self, request, queryset):
        n = queryset.update(approved=True)
        self.message_user(request, f"{n}개 승인 완료")

    @admin.action(description="승인 취소")
    def revoke_approval(self, request, queryset):
        n = queryset.update(approved=False)
        self.message_user(request, f"{n}개 승인 취소")


@admin.register(FishSpecies)
class FishSpeciesAdmin(admin.ModelAdmin):
    list_display = ("name", "rarity", "active","spawn_weight", "asset_link")
    list_filter = ("rarity", "active")
    search_fields = ("name",)
    list_editable = ("spawn_weight",) #등장 확률

    def asset_link(self, obj):
        return format_html(
            '<a href="/admin/manager/svgasset/{}/change/">{}</a>',
            obj.asset_id,
            obj.asset.name,
        )


@admin.register(BackgroundStyle)
class BackgroundStyleAdmin(admin.ModelAdmin):
    list_display = ("name", "active", "asset_link")
    list_filter = ("active",)
    search_fields = ("name",)

    def asset_link(self, obj):
        return format_html(
            '<a href="/admin/manager/svgasset/{}/change/">{}</a>',
            obj.asset_id,
            obj.asset.name,
        )
    
@admin.register(ShopItem)
class ShopItemAdmin(admin.ModelAdmin):
    list_display = ("name", "item_type", "price", "active", "preview_svg")
    list_editable = ("price", "active")
    list_filter = ("item_type", "active")
    search_fields = ("name",)

    def preview_svg(self, obj):
        if obj.asset and obj.asset.svg:
            return format_html(
                '<img src="{}" width="40" height="40" style="object-fit:contain;">',
                obj.asset.svg.url,
            )
        return "-"
    preview_svg.short_description = "미리보기"
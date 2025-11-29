from django.contrib import admin
from .models import UnlockedFish, OwnBackground, Aquarium, Fishtank, ContributionFish, FishtankSetting

@admin.register(UnlockedFish)
class UnlockedFishAdmin(admin.ModelAdmin):
    list_display = ('user', 'fish_species', 'unlocked_at')
    list_filter = ('user', 'fish_species')
    search_fields = ('user__username', 'fish_species__name')

@admin.register(OwnBackground)
class OwnBackgroundAdmin(admin.ModelAdmin):
    list_display = ('user', 'background', 'unlocked_at')
    list_filter = ('user', 'background')
    search_fields = ('user__username', 'background__name')

@admin.register(Aquarium)
class AquariumAdmin(admin.ModelAdmin):
    list_display = ('user', 'background', 'svg_path')
    search_fields = ('user__username',)

@admin.register(Fishtank)
class FishtankAdmin(admin.ModelAdmin):
    list_display = ('repository', 'svg_path')
    search_fields = ('repository__name',)

@admin.register(ContributionFish)
class ContributionFishAdmin(admin.ModelAdmin):
    # list_display 및 list_filter 수정
    list_display = ('contributor', 'fish_species', 'aquarium', 'is_visible_in_fishtank', 'is_visible_in_aquarium')
    list_filter = ('is_visible_in_fishtank', 'is_visible_in_aquarium', 'fish_species')
    search_fields = ('contributor__user__username', 'fish_species__name')

@admin.register(FishtankSetting)
class FishtankSettingAdmin(admin.ModelAdmin):
    list_display = ('fishtank', 'contributor', 'background')
    list_filter = ('fishtank', 'contributor')
    search_fields = ('fishtank__repository__name', 'contributor__username')
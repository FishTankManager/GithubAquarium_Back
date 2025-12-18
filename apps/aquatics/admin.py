from django.contrib import admin
from .models import UnlockedFish, OwnBackground, Aquarium, Fishtank, ContributionFish, FishtankSetting

@admin.register(UnlockedFish)
class UnlockedFishAdmin(admin.ModelAdmin):
    list_display = ('user', 'fish_species', 'unlocked_at')
    list_filter = ('unlocked_at', 'fish_species__rarity')
    search_fields = ('user__username', 'fish_species__name')

@admin.register(OwnBackground)
class OwnBackgroundAdmin(admin.ModelAdmin):
    list_display = ('user', 'background', 'unlocked_at')
    search_fields = ('user__username', 'background__name')

@admin.register(Aquarium)
class AquariumAdmin(admin.ModelAdmin):
    list_display = ('user', 'background', 'fish_count')
    
    def fish_count(self, obj):
        return obj.fishes.count()

@admin.register(Fishtank)
class FishtankAdmin(admin.ModelAdmin):
    list_display = ('repository', 'fish_count')

    def fish_count(self, obj):
        return obj.repository.contributors.count()

@admin.register(ContributionFish)
class ContributionFishAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_user', 'get_repo', 'fish_species', 'is_visible_in_fishtank', 'is_visible_in_aquarium')
    list_filter = ('is_visible_in_fishtank', 'is_visible_in_aquarium', 'fish_species__maturity')
    search_fields = ('contributor__user__username', 'contributor__repository__full_name')

    def get_user(self, obj):
        return obj.contributor.user.username
    get_user.short_description = 'User'

    def get_repo(self, obj):
        return obj.contributor.repository.name
    get_repo.short_description = 'Repository'

@admin.register(FishtankSetting)
class FishtankSettingAdmin(admin.ModelAdmin):
    list_display = ('fishtank', 'contributor', 'background')
from django.contrib import admin
from .models import FishSpecies, Background, Item

@admin.register(FishSpecies)
class FishSpeciesAdmin(admin.ModelAdmin):
    list_display = ('name', 'group_code', 'maturity', 'rarity', 'required_commits')
    list_filter = ('rarity', 'maturity', 'group_code')
    search_fields = ('name', 'group_code')
    ordering = ('group_code', 'maturity')

@admin.register(Background)
class BackgroundAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'has_image')
    search_fields = ('name', 'code')

    def has_image(self, obj):
        return bool(obj.background_image)
    has_image.boolean = True

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'item_type', 'price', 'is_active')
    list_filter = ('item_type', 'is_active')
    search_fields = ('name', 'code')
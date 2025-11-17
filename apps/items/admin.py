from django.contrib import admin
from .models import FishSpecies, Background

@admin.register(FishSpecies)
class FishSpeciesAdmin(admin.ModelAdmin):
    list_display = ('name', 'group_code', 'maturity', 'required_commits', 'rarity')
    list_filter = ('rarity', 'maturity', 'group_code')
    search_fields = ('name', 'group_code')
    ordering = ('group_code', 'maturity')

@admin.register(Background)
class BackgroundAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')
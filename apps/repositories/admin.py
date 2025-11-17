from django.contrib import admin
from .models import Repository, Contributor, Commit

@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'owner', 'language', 'stargazers_count', 'commit_count', 'last_synced_at')
    list_filter = ('language',)
    search_fields = ('full_name', 'owner__username')
    ordering = ('-stargazers_count',)

@admin.register(Contributor)
class ContributorAdmin(admin.ModelAdmin):
    list_display = ('user', 'repository', 'commit_count')
    search_fields = ('user__username', 'repository__full_name')
    ordering = ('-commit_count',)

@admin.register(Commit)
class CommitAdmin(admin.ModelAdmin):
    list_display = ('sha', 'repository', 'author', 'author_name', 'committed_at')
    list_filter = ('repository',)
    search_fields = ('sha', 'repository__full_name', 'author__username', 'author_name')
    ordering = ('-committed_at',)
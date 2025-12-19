from django.contrib import admin
from .models import Repository, Contributor, Commit

@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'owner', 'commit_count', 'stargazers_count', 'language', 'dirty_at', 'last_synced_at')
    list_filter = ('language', 'default_branch')
    search_fields = ('name', 'full_name', 'owner__username')
    readonly_fields = ('last_synced_at',) # 시스템에 의해 자동 업데이트되는 필드
    
    fieldsets = (
        ('Basic Info', {'fields': ('github_id', 'name', 'full_name', 'owner', 'html_url', 'description')}),
        ('Stats & Sync', {'fields': ('stargazers_count', 'language', 'commit_count', 'default_branch', 'last_synced_hash', 'dirty_at', 'last_synced_at')}),
    )

@admin.register(Contributor)
class ContributorAdmin(admin.ModelAdmin):
    list_display = ('user', 'repository', 'commit_count')
    list_filter = ('repository__language',)
    search_fields = ('user__username', 'repository__full_name')

@admin.register(Commit)
class CommitAdmin(admin.ModelAdmin):
    list_display = ('sha_short', 'repository', 'author', 'committed_at')
    list_filter = ('committed_at', 'repository__language')
    search_fields = ('sha', 'message', 'author_name', 'author_email')
    readonly_fields = ('committed_at',)

    def sha_short(self, obj):
        return obj.sha[:7]
    sha_short.short_description = 'SHA'
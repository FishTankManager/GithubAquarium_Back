from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # 리스트 화면에 표시할 필드
    list_display = ('username', 'email', 'github_username', 'github_id', 'is_staff', 'date_joined')
    # 필터링 옵션
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    # 검색 기능
    search_fields = ('username', 'email', 'github_username', 'github_id')
    # 상세 페이지 필드 구성
    fieldsets = UserAdmin.fieldsets + (
        ('GitHub Information', {'fields': ('github_id', 'github_username', 'avatar_url')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('GitHub Information', {'fields': ('github_id', 'github_username', 'avatar_url')}),
    )
    ordering = ('-date_joined',)
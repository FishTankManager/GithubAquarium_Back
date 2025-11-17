
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'github_id', 'github_username', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'github_username')
    ordering = ('username',)

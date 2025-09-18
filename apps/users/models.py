# apps/users/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Django의 기본 User 모델을 확장하여 GitHub 관련 정보를 추가합니다.
    """
    github_id = models.IntegerField(unique=True, null=True, blank=True)
    github_username = models.CharField(max_length=255, unique=True, null=True, blank=True)
    avatar_url = models.URLField(max_length=500, blank=True)

    def __str__(self):
        return self.username
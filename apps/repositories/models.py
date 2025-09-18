# apps/repositories/models.py

from django.db import models
from django.conf import settings

class Repository(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='repositories')
    github_id = models.BigIntegerField(unique=True)
    name = models.CharField(max_length=255)
    full_name = models.CharField(max_length=512)
    description = models.TextField(null=True, blank=True)
    html_url = models.URLField(max_length=512)
    stargazers_count = models.IntegerField(default=0)
    language = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    last_synced_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name

class Commit(models.Model):
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE, related_name='commits')
    sha = models.CharField(max_length=40, unique=True)
    author_name = models.CharField(max_length=255)
    author_email = models.EmailField()
    message = models.TextField()
    committed_at = models.DateTimeField()

    def __str__(self):
        return self.sha[:7]

class Contributor(models.Model):
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE, related_name='contributors')
    github_username = models.CharField(max_length=255)
    contributions = models.IntegerField()
    avatar_url = models.URLField(max_length=512)

    class Meta:
        unique_together = ('repository', 'github_username')

    def __str__(self):
        return self.github_username

# Stargazer 모델은 필요 시 추가할 수 있으나,
# 여기서는 stargazers_count만 Repository 모델에 저장하는 것으로 간소화했습니다.
# apps/repositories/models.py
from django.db import models
from apps.users.models import Owner

class Repository(models.Model):
    """
    GitHub Repository의 핵심 정보를 저장하는 모델입니다.
    """
    # Repository의 소유자를 User가 아닌 Owner 모델과 연결합니다.
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, related_name='repositories')
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

class Contributor(models.Model):
    """
    특정 Repository의 기여자에 대한 정보를 저장하는 모델입니다.
    GitHub API의 Contributor 정보를 기반으로 생성됩니다.
    """
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE, related_name='contributors')
    github_username = models.CharField(max_length=255)
    contributions = models.IntegerField()
    avatar_url = models.URLField(max_length=512, blank=True)

    class Meta:
        # 하나의 Repository 내에서 github_username은 고유해야 합니다.
        unique_together = ('repository', 'github_username')

    def __str__(self):
        return f"{self.github_username} in {self.repository.name}"

class Commit(models.Model):
    """
    특정 Repository에 속한 개별 커밋 정보를 저장하는 모델입니다.
    """
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE, related_name='commits')
    sha = models.CharField(max_length=40, unique=True)
    
    # GitHub API를 통해 식별된 Contributor와 연결합니다.
    # 매핑 실패 시(GitHub 계정과 연결되지 않은 커밋) null이 될 수 있습니다.
    author = models.ForeignKey(Contributor, on_delete=models.SET_NULL, null=True, blank=True, related_name='commits')
    
    # Git에 기록된 원본 작성자 정보를 별도로 저장합니다.
    author_name = models.CharField(max_length=255)
    author_email = models.EmailField()
    
    message = models.TextField()
    committed_at = models.DateTimeField()

    def __str__(self):
        return f"{self.sha[:7]} - {self.repository.name}"
# apps/repositories/models.py
from django.db import models
from apps.users.models import User

class Repository(models.Model):
    """
    GitHub Repository의 핵심 정보를 저장하는 모델입니다.
    """
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

    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,  # 소유 유저가 탈퇴해도 레포 정보는 유지
        null=True,
        blank=True,
        related_name='owned_repositories'
    )

    def __str__(self):
        return self.full_name

class Contributor(models.Model):
    """
    User와 Repository의 N:M 관계와 기여 요약 정보를 저장하는 중개 모델입니다.
    "어떤 유저가 어떤 레포지토리에 기여하는지"를 나타냅니다.
    """
    # N:M 관계 설정
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE, # 기여의 주체인 유저가 없으면 의미 없으므로 CASCADE
        related_name='contributions'
    )
    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        related_name='contributors'
    )

    # GitHub 유저 정보 및 요약 데이터
    github_username = models.CharField(max_length=255)
    contributions_count = models.IntegerField() # GitHub API 기준 총 기여 횟수
    avatar_url = models.URLField(max_length=512, blank=True)

    class Meta:
        # 하나의 Repository 내에서 동일한 User가 중복으로 기록되는 것을 방지합니다.
        unique_together = ('repository', 'user')

    def __str__(self):
        return f"{self.user.username} in {self.repository.name}"

class Commit(models.Model):
    """
    특정 Repository에 속한, 'User'가 작성한 개별 커밋 정보를 저장합니다.
    """
    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        related_name='commits'
    )
    
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL, # 작성 유저가 탈퇴해도 커밋 기록은 유지
        null=True,
        blank=True,
        related_name='commits' 
    )
    
    sha = models.CharField(max_length=40, unique=True)
    message = models.TextField()
    committed_at = models.DateTimeField()
    
    # Git에 기록된 원본 작성자 정보는 디버깅 등을 위해 유지합니다.
    author_name = models.CharField(max_length=255)
    author_email = models.EmailField()

    def __str__(self):
        return f"{self.sha[:7]} - {self.repository.name}"
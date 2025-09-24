# apps/users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q

class User(AbstractUser):
    """
    Django의 기본 User 모델을 확장하여 GitHub 계정 정보를 저장합니다.
    이 시스템에 로그인하는 사용자를 나타냅니다.
    """
    github_id = models.IntegerField(unique=True, null=True, blank=True)
    github_username = models.CharField(max_length=255, unique=True, null=True, blank=True)
    avatar_url = models.URLField(max_length=500, blank=True)

    def __str__(self):
        return self.username

class Organization(models.Model):
    """
    GitHub Organization 정보를 저장하는 모델입니다.
    Repository의 소유자가 될 수 있습니다.
    """
    github_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(null=True, blank=True)
    avatar_url = models.URLField(max_length=500, blank=True)

    def __str__(self):
        return self.name

class Owner(models.Model):
    """
    Repository의 소유자를 나타내는 중개 모델입니다.
    소유자는 User 또는 Organization일 수 있으며, 이 모델을 통해
    다형성 관계를 구현합니다.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    organization = models.OneToOneField(Organization, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        # Owner는 user 또는 organization 중 하나만 값을 가져야 한다는 제약조건
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(user__isnull=False, organization__isnull=True) |
                    Q(user__isnull=True, organization__isnull=False)
                ),
                name='owner_must_be_user_or_organization'
            )
        ]

    def __str__(self):
        if self.user:
            return f"User: {self.user.github_username}"
        if self.organization:
            return f"Organization: {self.organization.name}"
        return "Invalid Owner"

    @property
    def owner_details(self):
        """API 응답처럼 소유자 정보를 반환하는 헬퍼 프로퍼티입니다."""
        if self.user:
            return {
                "type": "User",
                "login": self.user.github_username,
                "avatar_url": self.user.avatar_url
            }
        if self.organization:
            return {
                "type": "Organization",
                "login": self.organization.name,
                "avatar_url": self.organization.avatar_url
            }
        return None
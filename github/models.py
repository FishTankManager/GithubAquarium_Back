from django.db import models
from users.models import User

class Repository(models.Model):
    repository_id = models.BigAutoField(primary_key=True, help_text="Service's internal unique ID")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='repositories')
    github_repository_id = models.BigIntegerField(unique=True, help_text="GitHub's immutable unique ID (used for webhooks, etc.)")
    repository_full_name = models.CharField(max_length=255, help_text="Display name (owner/repo)")
    commit_count = models.PositiveIntegerField(default=0)
    star_count = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['github_repository_id']),
        ]
        verbose_name_plural = "Repositories"

    def __str__(self):
        return self.repository_full_name
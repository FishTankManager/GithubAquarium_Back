from django.db import models
from users.models import User
from github.models import Repository

class FishBook(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    svg_bucket_path = models.CharField(max_length=255)
    max_level = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.id

class RepositoryFish(models.Model):
    fish = models.ForeignKey(FishBook, on_delete=models.CASCADE)
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE)
    is_visible = models.BooleanField(default=True)

    class Meta:
        unique_together = ('fish', 'repository')
        indexes = [
            models.Index(fields=['repository']),
        ]

    def __str__(self):
        return f"{self.fish_id} in {self.repository.repository_full_name}"

class BackgroundBook(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    svg_path = models.CharField(max_length=255)

    def __str__(self):
        return self.id

class UserOwnBackground(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    background = models.ForeignKey(BackgroundBook, on_delete=models.CASCADE)
    is_equipped = models.BooleanField(default=False, help_text="Indicates if this is the currently equipped background")

    class Meta:
        unique_together = ('user', 'background')

    def __str__(self):
        return f"{self.user.username} owns {self.background_id}"
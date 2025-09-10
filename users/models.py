from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    pass

class UserGithubAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='github_account')
    github_id = models.BigIntegerField(unique=True, help_text="GitHub's unique user ID")
    github_username = models.CharField(max_length=255, help_text="GitHub username (login)")
    installation_id = models.BigIntegerField(unique=True, null=True, blank=True, help_text="Unique ID for the GitHub App installation")
    access_token = models.TextField(null=True, blank=True, help_text="User access token for API calls (must be encrypted)")
    refresh_token = models.TextField(null=True, blank=True, help_text="Refresh token to renew the access token (must be encrypted)")

    def __str__(self):
        return self.github_username

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='profile')
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.user.username}'s profile"
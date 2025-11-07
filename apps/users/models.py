# apps/users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Custom User model that extends Django's AbstractUser.
    
    This model represents a user of the application and includes additional
    fields to store their GitHub account information, as authentication is
    handled via GitHub OAuth.
    """
    # GitHub's unique numeric ID for the user.
    github_id = models.BigIntegerField(unique=True, null=True, blank=True)
    
    # The user's login name on GitHub (e.g., "octocat").
    github_username = models.CharField(max_length=255, unique=True, null=True, blank=True)
    
    # URL for the user's GitHub profile picture.
    avatar_url = models.URLField(max_length=512, blank=True)

    def __str__(self):
        """
        Returns the username as the string representation of the User object.
        """
        return self.username
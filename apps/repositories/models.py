# apps/repositories/models.py
from django.db import models
from apps.users.models import User

class Repository(models.Model):
    """
    Stores the core information of a GitHub repository.
    """
    # GitHub's unique numeric ID for the repository.
    github_id = models.BigIntegerField(unique=True)
    
    # The name of the repository (e.g., "GithubAquarium_Back").
    name = models.CharField(max_length=255)
    
    # The full name of the repository, including the owner (e.g., "jay20012024/SNU").
    full_name = models.CharField(max_length=512)
    
    # The repository's description.
    description = models.TextField(null=True, blank=True)
    
    # The public URL of the repository on GitHub.
    html_url = models.URLField(max_length=512)
    
    # The number of users who have starred the repository.
    stargazers_count = models.IntegerField(default=0)
    
    # The primary programming language of the repository.
    language = models.CharField(max_length=100, null=True, blank=True)
    
    # The total number of commits in this repository.
    commit_count = models.PositiveIntegerField(
        default=0,
        help_text="The total number of commits in this repository."
    )
    
    # Timestamps from GitHub.
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    
    # Timestamp of the last time this record was synced with the GitHub API.
    last_synced_at = models.DateTimeField(auto_now=True)

    # Foreign key to the User who owns this repository.
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,  # Keep the repository record even if the owner is deleted.
        null=True,
        blank=True,
        related_name='owned_repositories'
    )

    # Additional fields for synchronization status
    default_branch = models.CharField(max_length=100, default='main')

    # latest synced commit hash
    last_synced_hash = models.CharField(max_length=40, null=True, blank=True)

    # by webhook
    dirty_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.full_name

class Contributor(models.Model):
    """
    Represents the many-to-many relationship between Users and Repositories.
    This model stores summary information about a user's contributions to a specific repository.
    """
    # The user who contributed.
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE, # If the user is deleted, this contribution record is also deleted.
        related_name='contributions'
    )
    # The repository that was contributed to.
    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE, # If the repository is deleted, this record is also deleted.
        related_name='contributors'
    )

    # --- Denormalized data from GitHub for performance ---
    # Total number of contributions to this repository.
    commit_count = models.IntegerField()

    class Meta:
        # Ensures that a user can only be listed as a contributor to a repository once.
        unique_together = ('repository', 'user')

    def __str__(self):
        return f"{self.user.username} in {self.repository.name}"

class Commit(models.Model):
    """
    Stores information about a single commit in a specific repository.
    """
    # The repository this commit belongs to.
    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        related_name='commits'
    )
    
    # The author of the commit, if they are a user of this application.
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL, # Keep the commit record even if the author's account is deleted.
        null=True,
        blank=True,
        related_name='commits' 
    )
    
    # The unique 40-character SHA hash of the commit.
    sha = models.CharField(max_length=40, unique=True)
    
    # The commit message.
    message = models.TextField()
    
    # The timestamp when the commit was authored.
    committed_at = models.DateTimeField()
    
    # --- Original author info from Git (for debugging and display) ---
    # This might differ from the `author` field if the committer is not a user of our app.
    author_name = models.CharField(max_length=255)
    author_email = models.EmailField()

    def __str__(self):
        return f"{self.sha[:7]} - {self.repository.name}"
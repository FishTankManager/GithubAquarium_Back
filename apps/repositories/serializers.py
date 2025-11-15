# apps/repositories/serializers.py
from rest_framework import serializers
from .models import Repository, Contributor, Commit

class RepositorySerializer(serializers.ModelSerializer):
    """
    Serializer for the Repository model.
    Converts Repository instances to JSON, including all fields.
    """
    class Meta:
        model = Repository
        fields = '__all__'

class ContributorSerializer(serializers.ModelSerializer):
    """
    Serializer for the Contributor model.
    Includes related user information for read-only purposes.
    """
    github_username = serializers.CharField(source='user.github_username', read_only=True)
    avatar_url = serializers.URLField(source='user.avatar_url', read_only=True)

    class Meta:
        model = Contributor
        fields = [
            'id',
            'user',
            'repository',
            'commit_count',
            'github_username',
            'avatar_url'
        ]

class CommitSerializer(serializers.ModelSerializer):
    """
    Serializer for the Commit model.
    Converts Commit instances to JSON, including all fields.
    """
    class Meta:
        model = Commit
        fields = '__all__'

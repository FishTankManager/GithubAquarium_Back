# apps/repositories/serializers.py
from rest_framework import serializers
from .models import Repository, Contributor, Commit

class RepositorySerializer(serializers.ModelSerializer):
    """
    Serializer for the Repository model.
    Converts Repository instances to JSON, including all fields.
    역참조 관계(contributors, commits)는 제외하여 순환 참조를 방지합니다.
    """
    class Meta:
        model = Repository
        fields = [
            'id',
            'github_id',
            'name',
            'full_name',
            'description',
            'html_url',
            'stargazers_count',
            'language',
            'commit_count',
            'created_at',
            'updated_at',
            'last_synced_at',
            'owner',
            'default_branch',
            'last_synced_hash',
            'dirty_at',
        ]

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

# apps/users/serializers.py
from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model.

    This serializer converts User model instances into JSON format, making them
    suitable for use in API endpoints. It defines the fields that should be
    included in the serialized output.
    """
    class Meta:
        model = User
        # Fields to include in the API representation of a User.
        fields = ('id', 'username', 'email', 'github_id', 'github_username', 'avatar_url')

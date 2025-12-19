from rest_framework import serializers
from .models import Repository
from apps.users.serializers import UserSerializer

class RepositoryListSerializer(serializers.ModelSerializer):
    # owner 필드에 UserSerializer를 중첩하여 ID뿐만 아니라 이름, 아바타 등 전체 정보를 반환
    owner = UserSerializer(read_only=True)
    
    # 로그인한 유저의 개인 기여도 필드 추가
    my_commit_count = serializers.SerializerMethodField(help_text="현재 로그인한 사용자의 해당 레포지토리 커밋 수")

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
            'commit_count',   # 레포지토리 전체 커밋 수
            'default_branch',
            'created_at', 
            'updated_at',
            'owner',          # 소유자 정보 (Object)
            'my_commit_count' # 내 기여도 (Integer)
        ]

    def get_my_commit_count(self, obj):
        user = self.context['request'].user
        if not user.is_authenticated:
            return 0
        
        # View에서 prefetch_related('contributors')를 사용하므로 메모리 내에서 조회하여 DB 부하 없음
        contributor = next((c for c in obj.contributors.all() if c.user_id == user.id), None)
        return contributor.commit_count if contributor else 0
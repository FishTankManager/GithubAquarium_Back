# apps/users/adapter.py

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
import requests

User = get_user_model()

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        """
        소셜 로그인 시 호출되며, User 모델에 추가 정보를 저장할 수 있습니다.
        GitHub API를 호출하여 사용자 정보를 업데이트합니다.
        """
        user = super().save_user(request, sociallogin, form)
        
        # GitHub API 호출을 위한 access token 가져오기
        try:
            github_account = sociallogin.account
            access_token = github_account.extra_data.get('access_token')
            
            if access_token:
                # 사용자 프로필 정보 업데이트 (예: avatar_url)
                headers = {'Authorization': f'token {access_token}'}
                user_api_url = 'https://api.github.com/user'
                response = requests.get(user_api_url, headers=headers)
                if response.status_code == 200:
                    user_data = response.json()
                    user.avatar_url = user_data.get('avatar_url')
                    user.github_username = user_data.get('login')
                    user.save()
                    
                # 여기에 저장소 정보를 가져오는 로직을 추가할 수 있습니다.
                # 예를 들어, Celery와 같은 비동기 태스크로 처리하는 것이 좋습니다.
                # from repositories.tasks import update_user_repositories
                # update_user_repositories.delay(user.id, access_token)

        except Exception as e:
            # 로깅 등을 통해 에러 처리
            print(f"Error updating user info from GitHub: {e}")
            
        return user
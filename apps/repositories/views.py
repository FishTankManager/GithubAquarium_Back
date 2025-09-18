# apps/repositories/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from allauth.socialaccount.models import SocialToken
import requests
from .models import Repository, Commit, Contributor
from datetime import datetime

class SyncRepositoriesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        
        try:
            # 사용자의 GitHub access token 가져오기
            github_token = SocialToken.objects.get(account__user=user, account__provider='github')
            access_token = github_token.token
        except SocialToken.DoesNotExist:
            return Response({'error': 'GitHub token not found.'}, status=400)

        headers = {'Authorization': f'token {access_token}'}
        
        # 1. 사용자 저장소 목록 가져오기
        repos_url = 'https://api.github.com/user/repos?type=owner&sort=updated'
        response = requests.get(repos_url, headers=headers)
        if response.status_code != 200:
            return Response({'error': 'Failed to fetch repositories from GitHub.'}, status=response.status_code)
            
        repos_data = response.json()
        
        # 2. 각 저장소 정보 DB에 업데이트/생성
        for repo_data in repos_data:
            repo, created = Repository.objects.update_or_create(
                github_id=repo_data['id'],
                defaults={
                    'owner': user,
                    'name': repo_data['name'],
                    'full_name': repo_data['full_name'],
                    'description': repo_data['description'],
                    'html_url': repo_data['html_url'],
                    'stargazers_count': repo_data['stargazers_count'],
                    'language': repo_data['language'],
                    'created_at': self._parse_datetime(repo_data['created_at']),
                    'updated_at': self._parse_datetime(repo_data['updated_at']),
                }
            )
            
            # 3. 각 저장소의 커밋, 기여자 정보 가져오기 (API 호출 횟수 주의!)
            # 이 부분은 역시 비동기 처리하는 것이 좋습니다.
            self._sync_commits(repo, headers)
            self._sync_contributors(repo, headers)

        return Response({'status': 'success', 'message': f'{len(repos_data)} repositories synced.'})

    def _sync_commits(self, repository, headers):
        commits_url = f'https://api.github.com/repos/{repository.full_name}/commits'
        response = requests.get(commits_url, headers=headers)
        if response.status_code == 200:
            for commit_data in response.json():
                Commit.objects.update_or_create(
                    sha=commit_data['sha'],
                    defaults={
                        'repository': repository,
                        'author_name': commit_data['commit']['author']['name'],
                        'author_email': commit_data['commit']['author']['email'],
                        'message': commit_data['commit']['message'],
                        'committed_at': self._parse_datetime(commit_data['commit']['author']['date']),
                    }
                )

    def _sync_contributors(self, repository, headers):
        contributors_url = f'https://api.github.com/repos/{repository.full_name}/contributors'
        response = requests.get(contributors_url, headers=headers)
        if response.status_code == 200:
            for contributor_data in response.json():
                Contributor.objects.update_or_create(
                    repository=repository,
                    github_username=contributor_data['login'],
                    defaults={
                        'contributions': contributor_data['contributions'],
                        'avatar_url': contributor_data['avatar_url'],
                    }
                )
    
    def _parse_datetime(self, datetime_str):
        # GitHub API는 ISO 8601 형식의 문자열을 반환합니다.
        # 'Z'는 UTC를 의미하므로, 이를 파싱하여 datetime 객체로 변환합니다.
        if datetime_str.endswith('Z'):
            datetime_str = datetime_str[:-1] + '+00:00'
        return datetime.fromisoformat(datetime_str)


# 이 뷰를 연결할 URL을 설정해야 합니다.
# GithubAquarium/urls.py 또는 repositories/urls.py
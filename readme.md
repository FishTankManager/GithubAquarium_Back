# uv 설치
curl -LsSf https://astral.sh/uv/install.sh | sh

# 도움 되는 명령어
uv run python3 manage.py graph_models -a -o erd.png
uv run ruff check . --fix
uv run python3 manage.py show_urls
git ls-files '*.py' | xargs -I {} sh -c 'echo "\n=== {} ===" && cat {}'  > all.txt

.env 예시 format
DEBUG=''
SECRET_KEY=''

GITHUB_APP_ID=''
GITHUB_CLIENT_ID=''
GITHUB_CLIENT_SECRET=''
GITHUB_PRIVATE_KEY_B64=""

GITHUB_WEBHOOK_SECRET=''
GITHUB_CALLBACK_URL=''
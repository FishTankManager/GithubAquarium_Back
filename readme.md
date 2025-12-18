# uv 설치
curl -LsSf https://astral.sh/uv/install.sh | sh

# 필요한 명령어
uv run manage.py collectstatic
uv run manage.py migrate
uv run manage.py graph_models -a -o erd.png
uv run manage.py show_urls
uv run ruff check . --fix
git ls-files '*.py' | xargs -I {} sh -c 'echo "\n=== {} ===" && cat {}'  > allcode.txt
tree -L 4 -I ".venv|__pycache__|.ruff_cache|staticfiles_collected|logs" > structure.txt

uv run python manage.py init_items # 커스텀
uv run python manage.py createsuperuser # 관리자 페이지용

# .env 예시 format
DEBUG=''
SECRET_KEY=''

GITHUB_APP_ID=''
GITHUB_CLIENT_ID=''
GITHUB_CLIENT_SECRET=''
GITHUB_PRIVATE_KEY_B64=""

GITHUB_WEBHOOK_SECRET=''
GITHUB_CALLBACK_URL=''
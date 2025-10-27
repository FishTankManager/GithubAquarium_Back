# uv 설치
curl -LsSf https://astral.sh/uv/install.sh | sh

# 도움 되는 명령어
uv run python3 manage.py graph_models -a -o erd.png
uv run ruff check . --fix
uv run python3 manage.py show_urls
find . \( -path "./venv" -o -path "./.venv" -o -path "./__pycache__" -o -path "./.git" \) -prune -o -name "*.py" -a -not -name "__init__.py" -exec sh -c 'echo "--- File: {} ---"; echo; cat {}; echo -e "\n\n";' \; > combined_code.txt

# TODO
celery worker 추가
docker로 db 연결 추가

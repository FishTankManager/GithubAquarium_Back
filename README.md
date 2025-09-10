# .env 초기 설정 FishTankManager에 등록된 github app 설정 확인할 것
GITHUB_APP_ID=''
GITHUB_CLIENT_ID=''
GITHUB_CLIENT_SECRET=''
GITHUB_PRIVATE_KEY_B64=""
SECRET_KEY=''

## 배포용 ubuntu 기초 세팅방법
### 경로문제 발생시 home에서부터 chmod 755 하면서 내려오기
0. ubuntu 업데이트
sudo apt update && sudo apt upgrade -y
sudo apt install -y nginx nodejs certbot python3-certbot-nginx
sudo systemctl start nginx   # 서비스 시작
sudo systemctl enable nginx  # 부팅 시 자동 시작
curl -LsSf https://astral.sh/uv/install.sh | sh # uv 설치

1. django, react 프로젝트 pull

2. react 폴더로 이동 
npm install
npm run build

3. django 폴더로 이동
uv sync
touch .env 및 vim .env로 필요한 내용 작성

4. 배포용 localhost worker run 커맨드
./.venv/bin/gunicorn -w 1 -k uvicorn.workers.UvicornWorker GithubAquarium.asgi:application --bind 0.0.0.0:8000 --daemon # 1개 worker 설정

5. http 서빙용 nginx 설정
sudo touch /etc/nginx/sites-available/githubaquarium.conf
sudo vim /etc/nginx/sites-available/githubaquarium.conf

server {
    listen 80; # http 요청 처리용
    server_name githubaquarium.store www.githubaquarium.store # 도메인 주소

    # React 정적 파일 서빙
    location / {
        root /home/ubuntu/LikeLion/~~~/build;  # React 빌드 절대 경로
        index index.html;
        try_files $uri /index.html;  # React 라우팅 지원 (SPA)
    }

    # 백엔드 프록시
    location /api/ {
        proxy_pass http://localhost:8000/;  # django worker 포트
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 어항 svg 파일 프록시
    location /fishTanks/ {
    root /home/ubuntu/static_files; # 정적 svg 파일이 있는 폴더 경로
    try_files $uri =404;
    }
}

sudo ln -s /etc/nginx/sites-available/githubaquarium.conf /etc/nginx/sites-enabled/ # 심볼릭 링크 생성

sudo nginx -t  # 설정 오류 확인
sudo systemctl restart nginx

6. cerbot을 통한 https 서빙용 SSL 인증 및 설정 자동화
sudo certbot --nginx -d githubaquarium.com
sudo nginx -t  # 설정 오류 확인
sudo systemctl restart nginx

## 도움 되는 명령어들
0. import 관계 정리 명령어
uv run ruff check --fix --extend-select I .

1. 심심할때 해보기
git ls-files | xargs wc -l
git ls-files | xargs wc -c
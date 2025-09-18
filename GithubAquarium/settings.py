# settings.py

import os
from pathlib import Path
import environ
import base64
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False)
)

environ.Env.read_env(
    env_file=os.path.join(BASE_DIR, '.env')
)

GITHUB_APP_ID = env('GITHUB_APP_ID')
GITHUB_CLIENT_ID = env('GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = env('GITHUB_CLIENT_SECRET')
SECRET_KEY = env('SECRET_KEY')
GITHUB_PRIVATE_KEY = base64.b64decode(str(env('GITHUB_PRIVATE_KEY_B64'))).decode('utf-8')
GITHUB_WEBHOOK_SECRET = env('GITHUB_WEBHOOK_SECRET')
DEBUG = env('DEBUG')

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'githubaquarium.store', 'www.githubaquarium.store']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    # DRF
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',

    # dj-rest-auth
    'dj_rest_auth',
    'dj_rest_auth.registration', 

    # django-allauth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.github',

    # CORS
    'corsheaders',

    # Your custom apps
    'apps.users',
    'apps.repositories',

    # development tools
    'django_extensions',
]

# allauth settings
SITE_ID = 1

# Authentication backends
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Social providers configuration (GitHub OAuth)
SOCIALACCOUNT_PROVIDERS = {
    'github': {
        'APP': {
            'client_id': GITHUB_CLIENT_ID,
            'secret': GITHUB_CLIENT_SECRET,
        },
        'SCOPE': [
            'read:user',
            'user:email',
            'repo',
        ],
        'AUTH_PARAMS': {'access_type': 'online'},
    }
}

# Disable traditional email/password signup/login to enforce GitHub OAuth only
ACCOUNT_ADAPTER = 'apps.users.adapter.CustomAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'apps.users.adapter.CustomSocialAccountAdapter'

ACCOUNT_SIGNUP_FIELDS = []
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = 'optional'  # Since GitHub provides verified emails

SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_REQUIRED = False  # GitHub may not always provide email

# To disable local registration, we'll assume custom adapter logic (not implemented here for brevity)
# In a custom adapter, override is_open_for_signup to return False for local accounts

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        # 세션 인증은 Django Admin 등 브라우저 기반 테스트용
        'rest_framework.authentication.SessionAuthentication', 
        # JWT 인증을 기본 인증 방식으로 설정
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# --- dj-rest-auth JWT 설정 ---
# dj-rest-auth가 JWT를 사용하도록 명시하고, 세션 로그인은 비활성화
REST_AUTH = {
    'USE_JWT': True,
    'SESSION_LOGIN': False, # API 서버는 상태를 저장하지 않는(stateless) JWT 방식을 따름
    'JWT_AUTH_HTTPONLY': True, # Refresh Token을 HttpOnly 쿠키에 저장하여 XSS 공격 방어
    'JWT_AUTH_COOKIE': 'my-app-auth', # Access Token을 저장할 쿠키 이름
    'JWT_AUTH_REFRESH_COOKIE': 'my-refresh-token', # Refresh Token을 저장할 쿠키 이름
    'JWT_AUTH_SAMESITE': 'Lax',
}

# --- djangorestframework-simplejwt 설정 ---
SIMPLE_JWT = {
    # Access Token 유효 기간 설정 (예: 1시간)
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    # Refresh Token 유효 기간 설정 (예: 14일)
    'REFRESH_TOKEN_LIFETIME': timedelta(days=14),
    
    # Refresh Token 재발급(rotation) 및 블랙리스트 설정 (보안 강화)
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    
    # 토큰 암호화 알고리즘 및 서명 키 설정
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    
    # 토큰 헤더 형식 정의
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    
    # User 모델과의 관계 설정
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    # 토큰 클래스 지정
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}



# CORS settings (add origins as needed, e.g., for frontend)
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',  # Example for local dev frontend
    'https://githubaquarium.store',
]
CORS_ALLOW_CREDENTIALS = True 

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # allauth middleware
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'GithubAquarium.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'GithubAquarium.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTH_USER_MODEL = 'users.User'

# Internationalization
LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
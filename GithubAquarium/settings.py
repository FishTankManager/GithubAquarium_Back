# settings.py

import os
from pathlib import Path
import environ
import base64

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
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# CORS settings (add origins as needed, e.g., for frontend)
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',  # Example for local dev frontend
    'https://githubaquarium.store',
]

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
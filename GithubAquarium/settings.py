# settings.py
import os
from pathlib import Path
import environ
import base64
from datetime import timedelta

# --- Core Paths and Environment Setup ---
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False)
)

environ.Env.read_env(
    env_file=os.path.join(BASE_DIR, '.env')
)

# --- Security and Core Django Settings ---
SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'githubaquarium.store', 'www.githubaquarium.store']

# --- GitHub Application Credentials ---
GITHUB_APP_ID = env('GITHUB_APP_ID')
GITHUB_CLIENT_ID = env('GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = env('GITHUB_CLIENT_SECRET')
GITHUB_PRIVATE_KEY = base64.b64decode(str(env('GITHUB_PRIVATE_KEY_B64'))).decode('utf-8')
GITHUB_WEBHOOK_SECRET = env('GITHUB_WEBHOOK_SECRET')
GITHUB_CALLBACK_URL = env('GITHUB_CALLBACK_URL')


# --- Application Definition ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    #'django.contrib.sites',

    # DRF
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    #'rest_framework_simplejwt.token_blacklist',

    # dj-rest-auth
    'dj_rest_auth',
    'dj_rest_auth.registration',

    # django-allauth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.github',

    # drf-yasg
    'drf_yasg',

    # CORS
    'corsheaders',

    # Your custom apps
    'apps.users',
    'apps.repositories',
    "apps.manager.apps.ManagerConfig",
    # Development tools
    'django_extensions',
]

# --- Middleware Configuration ---
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

# --- URL, Template, and WSGI Configuration ---
ROOT_URLCONF = 'GithubAquarium.urls'
WSGI_APPLICATION = 'GithubAquarium.wsgi.application'

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

# --- Database Configuration ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# --- Authentication and User Model ---
AUTH_USER_MODEL = 'users.User'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- Internationalization ---
LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True

# --- Static Files ---
STATIC_URL = 'static/'

# --- Default Primary Key ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# -----------------------------------------------------------------------------
# THIRD-PARTY LIBRARIES CONFIGURATION
# -----------------------------------------------------------------------------

# --- django-cors-headers Settings ---
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'https://githubaquarium.store',
]
CORS_ALLOW_CREDENTIALS = True

# --- django-allauth Settings ---
SITE_ID = 1

SOCIALACCOUNT_PROVIDERS = {
    'github': {
        'APP': {
            'client_id': GITHUB_CLIENT_ID,
            'secret': GITHUB_CLIENT_SECRET,
        },
        'SCOPE': [
            'user',
            'repo',
            'read:org',
        ],
        'AUTH_PARAMS': {'access_type': 'online'},
    }
}

SOCIALACCOUNT_ADAPTER = 'apps.users.adapter.CustomSocialAccountAdapter'
SOCIALACCOUNT_REQUESTS_TIMEOUT = 5
SOCIALACCOUNT_STORE_TOKENS = True
SOCIALACCOUNT_ONLY = True
ACCOUNT_EMAIL_VERIFICATION = 'none'

# --- djangorestframework (DRF) Settings ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        # for admin page login
        'rest_framework.authentication.SessionAuthentication',
        'dj_rest_auth.jwt_auth.JWTCookieAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# --- dj-rest-auth Settings ---
REST_AUTH = {
    'USER_DETAILS_SERIALIZER': 'apps.users.serializers.UserSerializer',
    'USE_JWT': True,
    'SESSION_LOGIN': False,
    'JWT_AUTH_HTTPONLY': True,
    'JWT_AUTH_COOKIE': 'my-app-auth',
    'JWT_AUTH_REFRESH_COOKIE': 'my-refresh-token',
    'JWT_AUTH_SAMESITE': 'Lax',
}

# --- djangorestframework-simplejwt Settings ---
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=14),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# -----------------------------------------------------------------------------
# LOGGING CONFIGURATION
# -----------------------------------------------------------------------------

LOG_DIR = BASE_DIR / 'logs'
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': LOG_DIR / 'django.log',
            'when': 'D',  # 매일 자정
            'interval': 1,
            'backupCount': 30,  # 30일치 로그 보관
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'DEBUG' if DEBUG else 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'WARNING',
            'propagate': False,
        },
        # Your app's logger
        'apps': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
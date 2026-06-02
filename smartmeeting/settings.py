# smartmeeting/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

AUTH_USER_MODEL = 'accounts.User'

# Секретный ключ - ОБЯЗАТЕЛЬНО из переменных окружения
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-ваш-ключ-тут')
# В production никогда не используйте значение по умолчанию!

# Debug - из переменных окружения
DEBUG = os.environ.get('DJANGO_DEBUG', 'False')

# ALLOWED_HOSTS - из переменных окружения
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',')

CSRF_TRUSTED_ORIGINS = os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',')

# Удаляем пустые строки
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in CSRF_TRUSTED_ORIGINS if origin.strip()]

# Если список пустой, можно установить значение по умолчанию
if not CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS = ['https://smartmeeting.galkin.online']

# CSRF cookie настройки
CSRF_COOKIE_SECURE = os.getenv('DJANGO_CSRF_COOKIE_SECURE', 'False') == 'True'
SESSION_COOKIE_SECURE = os.getenv('DJANGO_SESSION_COOKIE_SECURE', 'False') == 'True'
CSRF_COOKIE_HTTPONLY = False  # Важно для работы с JavaScript
CSRF_USE_SESSIONS = False  # Хранить CSRF токен в cookie, а не в сессии

# Приложения
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Сторонние приложения
    'django_celery_beat',
    'storages',

    # НАШИ ПРИЛОЖЕНИЯ
    'apps.accounts',
    'apps.rooms',
    'apps.bookings',
    'apps.notifications',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'smartmeeting.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'smartmeeting.wsgi.application'

# База данных - из переменных окружения
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_DATABASE', 'smartmeeting'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'postgres'),
        'HOST': os.environ.get('DB_HOST', 'postgres'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# Альтернативный вариант через DATABASE_URL (рекомендуется)
# import dj_database_url
# DATABASES = {
#     'default': dj_database_url.config(
#         default=os.environ.get('DATABASE_URL', 'postgres://postgres:postgres@postgres:5432/smartmeeting'),
#         conn_max_age=600
#     )
# }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Язык и время
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

# Статика и медиа
YC_STORAGE_BUCKET_NAME = os.getenv("YC_STORAGE_BUCKET_NAME")
YC_STORAGE_ACCESS_KEY = os.getenv("YC_STORAGE_ACCESS_KEY")
YC_STORAGE_SECRET_KEY = os.getenv("YC_STORAGE_SECRET_KEY")

AWS_S3_ENDPOINT_URL = "https://storage.yandexcloud.net"
AWS_S3_REGION_NAME = "ru-central1"
AWS_STORAGE_BUCKET_NAME = YC_STORAGE_BUCKET_NAME
AWS_ACCESS_KEY_ID = YC_STORAGE_ACCESS_KEY
AWS_SECRET_ACCESS_KEY = YC_STORAGE_SECRET_KEY

AWS_LOCATION = "static"
AWS_QUERYSTRING_AUTH = False
AWS_DEFAULT_ACL = "public-read"

STATIC_URL = f"https://storage.yandexcloud.net/{YC_STORAGE_BUCKET_NAME}/static/"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": YC_STORAGE_BUCKET_NAME,
            "access_key": YC_STORAGE_ACCESS_KEY,
            "secret_key": YC_STORAGE_SECRET_KEY,
            "endpoint_url": AWS_S3_ENDPOINT_URL,
            "region_name": AWS_S3_REGION_NAME,
            "location": AWS_LOCATION,
            "default_acl": "public-read",
            "querystring_auth": False,
            "object_parameters": {
                "CacheControl": "max-age=86400",
            },
        },
    },
}
# STATIC_URL = '/static/'
# STATICFILES_DIRS = [BASE_DIR / 'static']
# STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Celery
CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Email
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND', 
    'django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')

# Login/Logout
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
LOGIN_URL = '/accounts/login/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


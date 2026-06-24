"""Django settings for Prof. Toni Coimbra (app de configuração: core)."""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)
_env_file = BASE_DIR / '.env'
if _env_file.is_file():
    environ.Env.read_env(_env_file)

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])
PRODUCTION_SECURITY = env.bool('PRODUCTION_SECURITY', default=not DEBUG)


# Application definition

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

LOCAL_APPS = [
    'base',
    'accounts',
    'catalog',
    'classroom',
    'materials',
    'activities',
    'notifications',
]

INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

if PRODUCTION_SECURITY:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
        'SECURE_HSTS_INCLUDE_SUBDOMAINS',
        default=True,
    )
    SECURE_HSTS_PRELOAD = env.bool('SECURE_HSTS_PRELOAD', default=True)
else:
    SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=False)

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'notifications.context_processors.notification_summary',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database — PostgreSQL via DATABASE_URL (django-environ)
DATABASES = {
    'default': env.db('DATABASE_URL'),
}


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internationalization — UI em pt-BR, fuso de São Paulo

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True


# Static files (WhiteNoise) e media

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DATA_UPLOAD_MAX_MEMORY_SIZE = env.int(
    'DATA_UPLOAD_MAX_MEMORY_SIZE',
    default=30 * 1024 * 1024,
)
FILE_UPLOAD_MAX_MEMORY_SIZE = env.int(
    'FILE_UPLOAD_MAX_MEMORY_SIZE',
    default=5 * 1024 * 1024,
)

# Media protegida (materiais/entregas): fora de MEDIA_ROOT, sem URL pública.
# Servida só por view com checagem de permissão (ver base.storage).
PROTECTED_MEDIA_ROOT = BASE_DIR / 'protected_media'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}


# Email — nativo do Django. Sem host configurado em DEBUG: console.

EMAIL_HOST = env('EMAIL_HOST', default='')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='no-reply@prof.tonicoimbra.com')

if not EMAIL_HOST:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Acervo PROF-TONI — import remoto via GitHub (botão no catálogo).

ACERVO_GITHUB_REPO = env('ACERVO_GITHUB_REPO', default='elvertoni/head')
ACERVO_GITHUB_REF = env('ACERVO_GITHUB_REF', default='main')
ACERVO_GITHUB_TOKEN = env('ACERVO_GITHUB_TOKEN', default='')


# Auth — nativa do Django, login por email.

AUTH_USER_MODEL = 'accounts.User'
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'classroom:professor_dashboard'
LOGOUT_REDIRECT_URL = 'home'

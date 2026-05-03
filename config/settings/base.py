"""
Base settings shared across all environments.
"""

import os
from pathlib import Path
from datetime import timedelta
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    'storages',
]

LOCAL_APPS = [
    'apps.users',
    'apps.vendors',
    'apps.schools',
    'apps.students',
    'apps.products',
    'apps.orders',
    'apps.payments',
    'apps.audit',
    'apps.blog',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.audit.middleware.AuditLogMiddleware',
]

ROOT_URLCONF = 'config.urls'

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

WSGI_APPLICATION = 'config.wsgi.application'

# Custom User Model
AUTH_USER_MODEL = 'users.CustomUser'

# Database - MySQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME', default='eschoolkart_db'),
        'USER': config('DB_USER', default='root'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='127.0.0.1'),
        'PORT': config('DB_PORT', default='3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── Django REST Framework ────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'utils.pagination.StandardResultsPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# ─── JWT Settings ─────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(
        minutes=config('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', default=60, cast=int)
    ),
    'REFRESH_TOKEN_LIFETIME': timedelta(
        days=config('JWT_REFRESH_TOKEN_LIFETIME_DAYS', default=7, cast=int)
    ),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# ─── CORS ─────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000'
).split(',')
CORS_ALLOW_CREDENTIALS = True

# ─── Email ────────────────────────────────────────────────────────────────────
# Use console backend in DEBUG so OTPs appear in the terminal without SMTP config.
_email_host_user = config('EMAIL_HOST_USER', default='')
if config('DEBUG', default=True, cast=bool) and not _email_host_user:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

EMAIL_HOST         = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT         = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS      = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER    = _email_host_user
EMAIL_HOST_PASSWORD= config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@eschoolkart.com')

FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:3000')

# ─── Razorpay ─────────────────────────────────────────────────────────────────
RAZORPAY_KEY_ID = config('RAZORPAY_KEY_ID', default='')
RAZORPAY_KEY_SECRET = config('RAZORPAY_KEY_SECRET', default='')

# ─── API Docs ─────────────────────────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    'TITLE': 'eSchoolKart API',
    'DESCRIPTION': 'eSchoolKart.com — Multi-vendor school marketplace',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# ─── MySQL 5.7 Support Hack for Django 4.2+ ───────────────────────────────────
try:
    from django.db.backends.mysql.base import DatabaseWrapper
    DatabaseWrapper.check_database_version_supported = lambda self: None
except ImportError:
    pass

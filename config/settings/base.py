"""
Shared Django settings for Web Mail project.
Environment-specific overrides in dev.py and prod.py.
"""
import os
from pathlib import Path

from celery.schedules import crontab
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Secret key & debug (override in dev.py / prod.py)
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-changeme')
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    # whitenoise.runserver_nostatic must precede django.contrib.staticfiles
    # so it can intercept the runserver static-file handler.
    'whitenoise.runserver_nostatic',

    # Django built-ins
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_api_key',
    'corsheaders',
    'drf_spectacular',
    'drf_spectacular_sidecar',
    'django_filters',
    'django_otp',
    'django_otp.plugins.otp_totp',
    'django_otp.plugins.otp_static',
    'django_celery_beat',

    # Local apps
    'apps.accounts',
    'apps.authentication',
    'apps.domains',
    'apps.email_messages',
    'apps.email_templates',
    'apps.events',
    'apps.streams',
    'apps.suppressions',
    'apps.webhooks',
    'apps.analytics',
    'apps.billing',
    'tracking',
    'web',
    'cookie_consent',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',  # For 2FA
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.request_id_middleware.RequestIDMiddleware',
    'core.middleware.api_key_middleware.APIKeyRateLimitMiddleware',
    'core.middleware.ip_whitelist.IPWhitelistMiddleware',
    'core.middleware.audit.AuditMiddleware',
    'core.middleware.security_headers_middleware.SecurityHeadersMiddleware',
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
                'web.context_processors.site_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password hashing — Argon2id first, PBKDF2 as fallback for existing hashes
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
]

# Base URL used for generating absolute links (unsubscribe, tracking pixels)
BASE_URL = os.getenv('BASE_URL', 'http://localhost:8000')

# GeoIP2 — path to MaxMind GeoLite2-City.mmdb (download via deploy/01_server_setup.sh)
# Falls back gracefully to empty dict if file is missing (see tracking/views.py)
GEOIP_PATH = os.getenv('GEOIP_PATH', str(BASE_DIR / 'geoip'))

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8}
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication
AUTH_USER_MODEL = 'accounts.CustomUser'
AUTHENTICATION_BACKENDS = [
    'apps.authentication.backends.EmailBackend',
]

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
        'core.authentication.APIKeyAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'core.throttling.PerAPIKeyThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'api_key': '100/min',
    },
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'core.exceptions.handlers.custom_exception_handler',
}

# Spectacular (OpenAPI docs)
SPECTACULAR_SETTINGS = {
    'TITLE': 'Web Mail API',
    'DESCRIPTION': 'Email delivery service API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    # Allow unauthenticated access to /api/docs/, /api/redoc/, /api/schema/
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
    'SERVE_AUTHENTICATION': [],
    # Serve Swagger UI / ReDoc assets from the local sidecar package
    # instead of loading from an external CDN (which renders a blank page
    # when the CDN is unreachable).
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'REDOC_DIST': 'SIDECAR',
}

# CORS
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
CORS_ALLOW_CREDENTIALS = True

# Celery
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes

CELERY_BEAT_SCHEDULE = {
    'aggregate-daily-stats': {
        'task': 'workers.tasks.aggregate_stats.aggregate_daily_stats',
        'schedule': crontab(hour=1, minute=0),
    },
    'reset-monthly-quotas': {
        'task': 'workers.tasks.reset_quota.reset_monthly_quotas',
        'schedule': crontab(hour=0, minute=5, day_of_month=1),
    },
    'dispatch-scheduled-messages': {
        'task': 'workers.tasks.dispatch_scheduled.dispatch_scheduled_messages',
        'schedule': crontab(minute='*'),  # every minute
    },
    'decay-engagement-scores': {
        'task': 'workers.tasks.decay_scores.decay_engagement_scores',
        'schedule': crontab(hour=2, minute=0, day_of_month=1),  # 1st of month 02:00 UTC
    },
    'cleanup-old-events': {
        'task': 'workers.tasks.cleanup.cleanup_old_events',
        'schedule': crontab(hour=3, minute=30),  # nightly 03:30 UTC
    },
    'retry-stuck-messages': {
        'task': 'workers.tasks.retry_stuck.retry_stuck_messages',
        'schedule': crontab(minute='*/15'),  # every 15 minutes
    },
    'check-bounce-rates': {
        'task': 'workers.tasks.check_bounce_rate.check_bounce_rates',
        'schedule': crontab(minute=0),  # every hour
    },
    'rotate-dkim-keys': {
        'task': 'workers.tasks.rotate_dkim.rotate_dkim_keys',
        'schedule': crontab(hour=4, minute=0),  # daily at 04:00 UTC
    },
}

# ── Redis cache ───────────────────────────────────────────────────────────────
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.getenv('REDIS_CACHE_URL', 'redis://localhost:6379/2'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'IGNORE_EXCEPTIONS': True,  # degrade gracefully if Redis is down
        },
        'KEY_PREFIX': 'webmail',
        'TIMEOUT': 300,  # 5-minute default TTL
    }
}

# ── Paystack ──────────────────────────────────────────────────────────────────
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY', '')
PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY', '')

# Base URL for the React frontend (used when building Paystack redirect URLs)
FRONTEND_BASE_URL = os.getenv('FRONTEND_BASE_URL', 'http://localhost:3000')

# Public base URL used to build tracking pixel / click-redirect links
TRACKING_BASE_URL = os.getenv('TRACKING_BASE_URL', 'http://localhost:8000')

# CAN-SPAM §5(a)(6): physical mailing address appended to every outgoing email footer.
PHYSICAL_ADDRESS = os.getenv('PHYSICAL_ADDRESS', '')

# Email configuration (for Django notifications, not transactional emails)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Logging — JSON-structured output for ELK / Datadog / CloudWatch parsing.
# Falls back to plain text if python-json-logger is not installed.
_USE_JSON_LOGS = os.getenv('LOG_FORMAT', 'json').lower() == 'json'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter'
                  if _USE_JSON_LOGS else 'logging.Formatter',
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s',
        },
        'plain': {
            'format': '%(levelname)s %(asctime)s %(name)s %(message)s',
        },
    },
    'filters': {
        'require_debug_false': {'()': 'django.utils.log.RequireDebugFalse'},
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json' if _USE_JSON_LOGS else 'plain',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': os.getenv('LOG_LEVEL', 'INFO'),
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'WARNING'),
            'propagate': False,
        },
        'celery': {
            'handlers': ['console'],
            'level': os.getenv('CELERY_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}

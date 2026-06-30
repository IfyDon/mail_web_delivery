"""
Production settings – override base.py for production deployment.
"""
import os
from .base import *

DEBUG = False
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'example.com').split(',')

# Production database (PostgreSQL)
import dj_database_url
DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL', 'sqlite:///db.sqlite3'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Security settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

INSTALLED_APPS = INSTALLED_APPS + ['anymail']  # noqa: F405
EMAIL_BACKEND = 'anymail.backends.amazon_ses.EmailBackend'
ANYMAIL = {
    'AMAZON_SES_CLIENT_PARAMS': {
        'region_name': os.getenv('AWS_SES_REGION', 'us-east-1'),
        'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID', ''),
        'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY', ''),
    },
    'AMAZON_SES_CONFIGURATION_SET_NAME': 'webmail-events',
}

# CORS
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', 'https://example.com').split(',')

# Sentry error tracking
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_dsn = os.getenv('SENTRY_DSN', '').strip()
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
    )

# Logging is inherited from base.py (JSON-structured via python-json-logger).
# Override LOG_FORMAT / LOG_LEVEL / DJANGO_LOG_LEVEL via environment variables.

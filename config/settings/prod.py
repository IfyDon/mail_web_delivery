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

# Email backend — SendGrid via django-anymail (add 'anymail' to INSTALLED_APPS inherited from base)
# Switch to 'anymail.backends.amazon_ses.EmailBackend' for AWS SES.
INSTALLED_APPS = INSTALLED_APPS + ['anymail']  # noqa: F405
EMAIL_BACKEND = 'anymail.backends.sendgrid.EmailBackend'
ANYMAIL = {
    'SENDGRID_API_KEY': os.getenv('SENDGRID_API_KEY', ''),
}

# CORS
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', 'https://example.com').split(',')

# Sentry error tracking
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_dsn = os.getenv('SENTRY_DSN', '')
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
    )

# Logging is inherited from base.py (JSON-structured via python-json-logger).
# Override LOG_FORMAT / LOG_LEVEL / DJANGO_LOG_LEVEL via environment variables.

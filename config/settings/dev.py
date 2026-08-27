"""
Development settings – override base.py for local development.
"""
from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '*']

# Windows does not support POSIX semaphores used by the default prefork pool.
CELERY_WORKER_POOL = 'solo'

# Development database (SQLite)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Development email backend (console output)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# base.py's whitenoise ManifestStaticFilesStorage requires collectstatic to
# have already run (it looks up hashed filenames in a build-time manifest).
# Production builds run collectstatic in the Dockerfile; dev/CI never do, so
# any test that renders a template with {% static %} fails with "Missing
# staticfiles manifest entry" otherwise. Plain storage serves files as-is.
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Relaxed CORS for frontend development
CORS_ALLOWED_ORIGINS = ['http://localhost:3000', 'http://127.0.0.1:3000']
CORS_ALLOW_CREDENTIALS = True

# Django Debug Toolbar.
# Its overlay has z-index:100000000 and captures every click on whatever
# HTML page it renders on, which breaks interactive UI (nav dropdowns, theme
# toggle, Swagger "Try it out", etc). So keep it OFF the landing site AND the
# API doc UIs (Swagger/ReDoc/schema), which are also HTML pages. It still
# renders on /admin/ and the toolbar's own /__debug__/ panels.
INSTALLED_APPS += ['debug_toolbar']  # noqa: F821
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']  # noqa: F821
INTERNAL_IPS = ['127.0.0.1', 'localhost']


def _show_debug_toolbar(request):
    # The doc UIs live under /api/ but must stay overlay-free.
    if request.path.startswith(('/api/docs', '/api/redoc', '/api/schema')):
        return False
    return request.path.startswith(('/admin/', '/__debug__/'))


DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': _show_debug_toolbar,
}

# Logging for development
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
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}

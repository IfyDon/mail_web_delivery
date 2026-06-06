import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

app = Celery('web_mail')

app.config_from_object('django.conf:settings', namespace='CELERY')

# Discover tasks in INSTALLED_APPS and explicitly in the workers package
# (workers/ is not a Django app so autodiscover_tasks() alone won't find it)
app.autodiscover_tasks()
app.autodiscover_tasks(['workers'])
